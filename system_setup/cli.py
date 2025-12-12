"""Command-line interface for system setup."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from system_setup import __version__
from system_setup.config import Config
from system_setup.logger import get_logger, setup_logger
from system_setup.platform import detect_platform
from system_setup.state import StateManager
from system_setup.tasks.registry import get_registry


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    # Get available tasks for help text
    registry = get_registry()
    available_tasks = registry.list_tasks()

    parser = argparse.ArgumentParser(
        description="Cross-platform system setup and configuration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s                          # Interactive setup with all tasks
  %(prog)s --yes                    # Unattended setup (auto-yes to prompts)
  %(prog)s --only=packages          # Only install packages
  %(prog)s --skip=hyprland,fish     # Skip specific tasks
  %(prog)s --profile=server         # Use server profile
  %(prog)s --dry-run                # Preview changes without applying
  %(prog)s --resume                 # Resume from previous interrupted run
  %(prog)s --list-tasks             # List all available tasks
  %(prog)s --list-profiles          # List available profiles

Available Tasks:
  {', '.join(available_tasks)}

Available Profiles:
  server, desktop, developer, minimal
  (Use --list-profiles for details)

Configuration:
  Create ~/.system_setup.yaml to override defaults:

  packages:
    additional:
      - docker
      - terraform

  # Override default packages for a platform
  packages:
    macos:
      formulae:
        - my-custom-formula

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
        metavar='TASKS',
        help=f'Comma-separated list of tasks to run. Available: {", ".join(available_tasks)}',
    )

    parser.add_argument(
        '--skip',
        metavar='TASKS',
        help='Comma-separated list of tasks to skip',
    )

    parser.add_argument(
        '--profile',
        metavar='NAME',
        help='Use a predefined profile (server, desktop, developer, minimal)',
    )

    parser.add_argument(
        '--list-tasks',
        action='store_true',
        help='List all available tasks with descriptions',
    )

    parser.add_argument(
        '--list-profiles',
        action='store_true',
        help='List available profiles with descriptions',
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
        help='Resume from previous state (uses ~/.system_setup_state)',
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


def get_tasks_to_run(
    config: Config,
    only_tasks: Optional[str],
    skip_tasks: Optional[str],
    available_tasks: List[str],
) -> List[str]:
    """
    Determine which tasks to run based on CLI arguments and profile.

    Args:
        config: Configuration instance (may have profile skip_tasks)
        only_tasks: Comma-separated tasks to run (if specified)
        skip_tasks: Comma-separated tasks to skip
        available_tasks: All available task names

    Returns:
        Ordered list of task names to execute
    """
    if only_tasks:
        # Parse comma-separated task list
        requested = [t.strip() for t in only_tasks.split(',')]
        invalid = [t for t in requested if t not in available_tasks]
        if invalid:
            raise ValueError(
                f"Unknown task(s): {', '.join(invalid)}. "
                f"Available tasks: {', '.join(available_tasks)}"
            )
        return requested

    # Start with configured task order, filtered to available tasks
    task_order = config.task_order
    tasks = [t for t in task_order if t in available_tasks]

    # Add any registered tasks not in order
    for task in available_tasks:
        if task not in tasks:
            tasks.append(task)

    # Build skip set from profile and CLI
    skip_set = set(config.profile_skip_tasks)
    if skip_tasks:
        skip_set.update(t.strip() for t in skip_tasks.split(','))

    # Remove skipped tasks
    tasks = [t for t in tasks if t not in skip_set]

    return tasks


def list_tasks(config: Config, state: StateManager, platform) -> None:
    """Display list of available tasks with descriptions."""
    registry = get_registry()
    print("\nAvailable Tasks:")
    print("=" * 70)

    for name in registry.list_tasks():
        info = registry.get_task_info(name, config, state, platform)
        if info:
            status = "✓" if info['complete'] else " "
            print(f"  [{status}] {name:15} - {info['description']}")
            if not info['supported']:
                print(f"       └── Not supported on this platform")
            if info['depends_on']:
                print(f"       └── Depends on: {', '.join(info['depends_on'])}")

    print()
    print("Legend: [✓] = completed")
    print()


def list_profiles(config: Config) -> None:
    """Display available profiles with descriptions."""
    profiles = config.list_profiles()

    print("\nAvailable Profiles:")
    print("=" * 70)

    if not profiles:
        print("  No profiles defined")
    else:
        active = config.active_profile
        for name, description in profiles.items():
            marker = " *" if name == active else ""
            print(f"  {name:15} - {description}{marker}")

    print()
    if config.active_profile:
        print(f"Active profile: {config.active_profile}")
        if config.profile_skip_tasks:
            print(f"Skipped tasks: {', '.join(config.profile_skip_tasks)}")
    print()
    print("Usage: ./run.py --profile=server")
    print()


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --reset flag (before logger init)
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
        # Load configuration with profile
        try:
            config = Config(config_path=args.config, profile=args.profile)
        except ValueError as e:
            logger.error(str(e))
            return 2

        # Initialize state manager
        state = StateManager()

        # Detect platform
        platform = detect_platform()

        # Handle --list-profiles
        if args.list_profiles:
            list_profiles(config)
            return 0

        # Handle --list-tasks
        if args.list_tasks:
            list_tasks(config, state, platform)
            return 0

        # Get registry
        registry = get_registry()
        available_tasks = registry.list_tasks()

        # Validate --only argument (basic validation before get_tasks_to_run)
        if args.only:
            requested = [t.strip() for t in args.only.split(',')]
            invalid = [t for t in requested if t not in available_tasks]
            if invalid:
                logger.error(
                    f"Unknown task(s): {', '.join(invalid)}. "
                    f"Available tasks: {', '.join(available_tasks)}"
                )
                return 2

        # Show resume status
        if args.resume:
            completed = state.get_completed_steps()
            if completed:
                logger.info("Resuming from previous state:")
                for step in completed:
                    logger.info(f"  ✓ {step}")
            else:
                logger.info("No previous state found")

        logger.info(f"Detected platform: {platform}")

        # Show profile info
        if config.active_profile:
            logger.info(f"Using profile: {config.active_profile}")
            if config.profile_skip_tasks:
                logger.info(f"Profile skips: {', '.join(config.profile_skip_tasks)}")

        # Show dry-run mode
        if args.dry_run:
            logger.warning("DRY RUN MODE - No changes will be made")

        if args.auto_yes:
            logger.info("AUTO YES MODE - All prompts will be automatically accepted")

        # Determine tasks to run
        try:
            tasks_to_run = get_tasks_to_run(
                config=config,
                only_tasks=args.only,
                skip_tasks=args.skip,
                available_tasks=available_tasks,
            )
        except ValueError as e:
            logger.error(str(e))
            return 2

        logger.info(f"Tasks to run: {', '.join(tasks_to_run)}")

        # Run tasks
        success = True
        for task_name in tasks_to_run:
            task = registry.create_task(
                name=task_name,
                config=config,
                state=state,
                platform=platform,
                dry_run=args.dry_run,
                auto_yes=args.auto_yes,
            )

            if task is None:
                logger.warning(f"Could not create task: {task_name}")
                continue

            # Check platform support
            if hasattr(task, 'is_supported') and not task.is_supported():
                logger.info(f"Skipping {task_name}: not supported on this platform")
                continue

            # Run task (tasks handle their own section headers)
            if not task.run():
                logger.error(f"Task failed: {task_name}")
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
