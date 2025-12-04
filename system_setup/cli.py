"""Command-line interface for system setup."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from system_setup import __version__
from system_setup.config import Config
from system_setup.logger import get_logger, setup_logger
from system_setup.packages import get_package_manager
from system_setup.platform import detect_platform
from system_setup.state import StateManager
from system_setup.tasks import DotfilesTask, SettingsTask, ShellTask


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Cross-platform system setup and configuration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Interactive setup with all sections
  %(prog)s --yes                    # Unattended setup (auto-yes to prompts)
  %(prog)s --only=packages          # Only install packages
  %(prog)s --dry-run                # Preview changes without applying
  %(prog)s --resume                 # Resume from previous interrupted run
  %(prog)s --reset                  # Clear state and start fresh

Configuration:
  Create ~/.system_setup.yaml or ./system_setup.yaml with settings:

  packages:
    additional_packages:
      - docker
      - terraform

  security:
    profile: normal  # normal, strict, reduced

  dotfiles:
    gdrive_id: YOUR_GOOGLE_DRIVE_FILE_ID
    checksum: YOUR_SHA256_HASH  # or 'skip'
    checksum_required: false

Exit Codes:
  0: Success
  1: General error
  2: Invalid arguments
  3: Missing dependencies
        """,
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        dest='auto_yes',
        help='Auto-answer yes to all prompts (unattended mode)',
    )

    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        help='Show what would be done without doing it',
    )

    parser.add_argument(
        '--only',
        choices=['packages', 'settings', 'dotfiles', 'shell'],
        help='Run only specified section',
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output',
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress console output (still logs to file)',
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help=f'Resume from previous state (uses ~/.system_setup_state)',
    )

    parser.add_argument(
        '--reset',
        action='store_true',
        help='Clear state file and start fresh',
    )

    parser.add_argument(
        '--config',
        type=Path,
        help='Path to configuration file',
    )

    parser.add_argument(
        '--log-file',
        type=Path,
        help='Path to log file (default: /tmp/system_setup_TIMESTAMP.log)',
    )

    return parser


def should_run_section(section: str, only_section: Optional[str]) -> bool:
    """Check if a section should be run."""
    if only_section is None:
        return True
    return only_section == section


def install_packages(
    platform,
    config: Config,
    state: StateManager,
    dry_run: bool,
    auto_yes: bool,
) -> bool:
    """Install packages for the platform."""
    logger = get_logger()

    if state.is_complete('packages_installed'):
        logger.info("Packages already installed (skipping)")
        return True

    # Get package manager
    pkg_manager = get_package_manager(platform, dry_run=dry_run)
    if not pkg_manager:
        logger.error("No suitable package manager found")
        return False

    logger.info(f"Using package manager: {pkg_manager.name}")

    # Update package manager
    logger.info("Updating package manager...")
    if not pkg_manager.update():
        logger.warning("Package manager update failed (continuing anyway)")

    # Define package lists by platform
    packages = []
    if platform.is_macos:
        packages = [
            'bat', 'eza', 'fnm', 'fzf', 'gdown', 'htop', 'neovim',
            'pyright', 'ripgrep', 'svn', 'tealdeer', 'wget', 'zoxide', 'zsh',
            # Casks
            'visual-studio-code.cask', 'alfred.cask', 'iterm2.cask',
            'dropbox.cask', 'cloudflare-warp.cask',
        ]
    elif platform.is_linux:
        if platform.distro == 'debian':
            packages = [
                'bat', 'curl', 'fzf', 'git', 'htop', 'neovim',
                'python3-pip', 'ripgrep', 'wget', 'zsh',
            ]
        elif platform.distro == 'arch':
            packages = [
                'bat', 'curl', 'eza', 'fnm', 'fzf', 'git', 'htop',
                'neovim', 'python-pip', 'ripgrep', 'wget', 'zsh',
            ]
    elif platform.is_windows:
        packages = [
            'Git.Git', 'Microsoft.VisualStudioCode',
            'Microsoft.PowerShell', 'JanDeDobbeleer.OhMyPosh',
        ]

    # Add additional packages from config
    packages.extend(config.additional_packages)

    if not packages:
        logger.warning("No packages defined for this platform")
        state.mark_complete('packages_installed')
        return True

    # Ask for confirmation
    if not auto_yes:
        logger.info(f"Packages to install: {', '.join(packages)}")
        response = input("Install packages? (y/N): ")
        if response.lower() not in ('y', 'yes'):
            logger.info("Skipping package installation")
            return True

    # Install packages
    logger.info(f"Installing {len(packages)} packages...")
    if pkg_manager.install(packages):
        logger.success(f"Installed {len(packages)} packages")
        for pkg in packages:
            logger.track_package(pkg)
        state.mark_complete('packages_installed')
        return True
    else:
        logger.error("Package installation failed")
        return False


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --reset flag
    if args.reset:
        state = StateManager()
        state.clear()
        print("State cleared. Run again to start fresh.")
        return 0

    # Initialize logger
    setup_logger(
        log_file=args.log_file,
        verbose=args.verbose,
        quiet=args.quiet,
    )
    logger = get_logger()

    try:
        # Load configuration
        config = Config(config_path=args.config)

        # Initialize state manager
        state = StateManager()

        # Show resume status
        if args.resume:
            completed = state.get_completed_steps()
            if completed:
                logger.info("Resuming from previous state:")
                for step in completed:
                    logger.info(f"  ✓ {step}")
            else:
                logger.info("No previous state found")

        # Detect platform
        platform = detect_platform()
        logger.info(f"Detected platform: {platform}")

        # Show dry-run mode
        if args.dry_run:
            logger.warning("DRY RUN MODE - No changes will be made")

        if args.auto_yes:
            logger.info("AUTO YES MODE - All prompts will be automatically accepted")

        # Run sections
        success = True

        # Packages
        if should_run_section('packages', args.only):
            logger.section("Package Installation")
            if not install_packages(platform, config, state, args.dry_run, args.auto_yes):
                success = False

        # Dotfiles
        if should_run_section('dotfiles', args.only):
            dotfiles_task = DotfilesTask(
                config=config,
                state=state,
                dry_run=args.dry_run,
                auto_yes=args.auto_yes,
            )
            if not dotfiles_task.run():
                success = False

        # Settings
        if should_run_section('settings', args.only):
            settings_task = SettingsTask(
                config=config,
                state=state,
                platform=platform,
                dry_run=args.dry_run,
                auto_yes=args.auto_yes,
            )
            if not settings_task.run():
                success = False

        # Shell
        if should_run_section('shell', args.only):
            shell_task = ShellTask(
                config=config,
                state=state,
                platform=platform,
                dry_run=args.dry_run,
                auto_yes=args.auto_yes,
            )
            if not shell_task.run():
                success = False

        # Show summary
        logger.show_summary()

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
