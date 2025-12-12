"""Hyprland desktop environment setup task."""

import shutil
from pathlib import Path
from typing import Dict, List

from system_setup.packages.factory import get_package_manager, ensure_paru_installed
from system_setup.tasks.base import BaseTask


# Package groups for Hyprland ecosystem
HYPRLAND_CORE_PACKAGES = [
    'hyprland',
    'hyprlock',
    'hypridle',
    'hyprshot',
    'xdg-desktop-portal-hyprland',
]

HYPRLAND_UTILS_PACKAGES = [
    'swww',           # Wallpaper daemon
    'waypaper',       # Wallpaper GUI
    'wl-clipboard',   # Clipboard
    'cliphist',       # Clipboard history
    'grim',           # Screenshots
    'slurp',          # Screen region selector
    'satty',          # Screenshot annotation
    'wf-recorder',    # Screen recording
    'brightnessctl',  # Brightness control
]

HYPRLAND_AUR_PACKAGES = [
    'ags-hyprpanel-git',  # HyprPanel bar
    'walker',             # App launcher
]

TERMINAL_PACKAGES = [
    'ghostty',        # Modern terminal
]

TERMINAL_AUR_PACKAGES = [
    # ghostty might be in AUR depending on distro
]

FILE_MANAGER_PACKAGES = [
    'nemo',           # GUI file manager
    'yazi',           # TUI file manager
    'ffmpegthumbnailer',
    'p7zip',
    'jq',
    'poppler',
    'fd',
    'ripgrep',
    'fzf',
    'zoxide',
]


class HyprlandTask(BaseTask):
    """Sets up complete Hyprland desktop environment."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize Hyprland setup task."""
        super().__init__(*args, **kwargs)
        self.home = Path.home()
        self.config_dir = self.home / '.config'

    @property
    def name(self) -> str:
        return 'hyprland'

    @property
    def description(self) -> str:
        return 'Hyprland Desktop Environment Setup'

    @property
    def state_key(self) -> str:
        return 'hyprland_setup'

    @property
    def platforms(self) -> list[str]:
        return ['linux']

    def run(self) -> bool:
        """
        Execute Hyprland setup task.

        Returns:
            True if successful
        """
        if not self.is_supported():
            self.logger.info("Hyprland is only supported on Linux")
            return True

        if self.skip_if_complete():
            return True

        self.logger.section(self.description)

        if not self.auto_yes:
            response = input("Set up Hyprland desktop environment? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipped Hyprland setup")
                return True

        steps = [
            ('hyprland_packages', self._install_packages),
            ('hyprland_config', self._configure_hyprland),
            ('hyprland_hyprlock', self._configure_hyprlock),
            ('hyprland_hypridle', self._configure_hypridle),
            ('hyprland_panel', self._configure_panel),
            ('hyprland_launcher', self._configure_launcher),
            ('hyprland_keybinds', self._create_keybinds_helper),
        ]

        for step_name, step_func in steps:
            if self.state.is_complete(step_name):
                self.logger.info(f"Step {step_name} already complete (skipping)")
                continue

            if not step_func():
                self.logger.error(f"Failed at step: {step_name}")
                return False

            self.state.mark_complete(step_name)

        self.mark_complete()
        self.logger.success("Hyprland setup complete!")
        return True

    def _install_packages(self) -> bool:
        """Install Hyprland packages."""
        self.logger.info("Installing Hyprland packages...")

        # Ensure paru is available for AUR packages
        if not ensure_paru_installed(self.dry_run):
            self.logger.warning("Could not install paru, some packages may be unavailable")

        pkg_manager = get_package_manager(self.platform, self.dry_run)
        if not pkg_manager:
            self.logger.error("No package manager found")
            return False

        # Install official packages
        all_packages = (
            HYPRLAND_CORE_PACKAGES +
            HYPRLAND_UTILS_PACKAGES +
            TERMINAL_PACKAGES +
            FILE_MANAGER_PACKAGES
        )

        self.logger.info(f"Installing {len(all_packages)} packages...")
        if not pkg_manager.install(all_packages):
            self.logger.warning("Some official packages failed to install")

        # Install AUR packages if paru available
        if pkg_manager.name == 'paru':
            aur_packages = HYPRLAND_AUR_PACKAGES + TERMINAL_AUR_PACKAGES
            self.logger.info(f"Installing {len(aur_packages)} AUR packages...")
            if not pkg_manager.install(aur_packages):
                self.logger.warning("Some AUR packages failed to install")

        return True

    def _configure_hyprland(self) -> bool:
        """Configure Hyprland main config."""
        self.logger.info("Configuring Hyprland...")

        hypr_dir = self.config_dir / 'hypr'
        hypr_dir.mkdir(parents=True, exist_ok=True)

        config_path = hypr_dir / 'hyprland.conf'

        # Get theme colors from config
        theme = self.config.get('hyprland.theme', 'catppuccin-mocha')
        terminal = self.config.get('hyprland.terminal', 'ghostty')
        file_manager = self.config.get('hyprland.file_manager', 'nemo')
        launcher = self.config.get('hyprland.launcher', 'walker')

        # Theme-specific colors
        colors = self._get_theme_colors(theme)

        config_content = self._generate_hyprland_config(
            terminal=terminal,
            file_manager=file_manager,
            launcher=launcher,
            colors=colors,
        )

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would write Hyprland config to {config_path}")
            return True

        config_path.write_text(config_content)
        self.logger.success(f"Created {config_path}")
        return True

    def _generate_hyprland_config(
        self,
        terminal: str,
        file_manager: str,
        launcher: str,
        colors: Dict[str, str],
    ) -> str:
        """Generate hyprland.conf content."""
        return f'''# Hyprland Configuration
# Generated by system-setup

################
### MONITORS ###
################

monitor=,preferred,auto,auto

###################
### MY PROGRAMS ###
###################

$terminal = {terminal}
$fileManager = {file_manager}
$menu = {launcher}

#################
### AUTOSTART ###
#################

exec-once = hyprpanel
exec-once = swww-daemon
exec-once = systemctl --user start elephant
exec-once = walker --gapplication-service
exec-once = hypridle
exec-once = wl-paste --type text --watch cliphist store
exec-once = wl-paste --type image --watch cliphist store

#############################
### ENVIRONMENT VARIABLES ###
#############################

env = XCURSOR_SIZE,24
env = HYPRCURSOR_SIZE,24
env = QT_QPA_PLATFORMTHEME,qt6ct
env = QT_STYLE_OVERRIDE,kvantum
env = XCURSOR_THEME,catppuccin-mocha-dark-cursors

#####################
### LOOK AND FEEL ###
#####################

general {{
    gaps_in = 4
    gaps_out = 8
    border_size = 2
    col.active_border = {colors['active_border']}
    col.inactive_border = {colors['inactive_border']}
    resize_on_border = false
    allow_tearing = false
    layout = dwindle
}}

decoration {{
    rounding = 10
    rounding_power = 2
    active_opacity = 1.0
    inactive_opacity = 1.0
    shadow {{
        enabled = true
        range = 4
        render_power = 3
        color = rgba(1a1a1aee)
    }}
    blur {{
        enabled = true
        size = 3
        passes = 1
        vibrancy = 0.1696
    }}
}}

animations {{
    enabled = yes
    bezier = easeOutQuint,0.23,1,0.32,1
    bezier = easeInOutCubic,0.65,0.05,0.36,1
    bezier = linear,0,0,1,1
    bezier = almostLinear,0.5,0.5,0.75,1.0
    bezier = quick,0.15,0,0.1,1
    animation = global, 1, 10, default
    animation = border, 1, 5.39, easeOutQuint
    animation = windows, 1, 4.79, easeOutQuint
    animation = windowsIn, 1, 4.1, easeOutQuint, popin 87%
    animation = windowsOut, 1, 1.49, linear, popin 87%
    animation = fadeIn, 1, 1.73, almostLinear
    animation = fadeOut, 1, 1.46, almostLinear
    animation = fade, 1, 3.03, quick
    animation = layers, 1, 3.81, easeOutQuint
    animation = layersIn, 1, 4, easeOutQuint, fade
    animation = layersOut, 1, 1.5, linear, fade
    animation = fadeLayersIn, 1, 1.79, almostLinear
    animation = fadeLayersOut, 1, 1.39, almostLinear
    animation = workspaces, 1, 1.94, almostLinear, fade
    animation = workspacesIn, 1, 1.21, almostLinear, fade
    animation = workspacesOut, 1, 1.94, almostLinear, fade
}}

dwindle {{
    pseudotile = true
    preserve_split = true
}}

master {{
    new_status = master
}}

misc {{
    force_default_wallpaper = -1
    disable_hyprland_logo = false
}}

#############
### INPUT ###
#############

input {{
    kb_layout = us
    follow_mouse = 1
    sensitivity = 0
    touchpad {{
        natural_scroll = true
    }}
}}

gestures {{
    workspace_swipe = false
}}

# Touchpad gestures
gesture = 3, horizontal, workspace

####################
### KEYBINDINGSS ###
####################

$mainMod = SUPER

# Core bindings
bind = $mainMod, T, exec, hyprctl dispatch "fullscreen 0 unset" && hyprctl dispatch "fullscreen 1 unset"; $terminal
bind = $mainMod, Q, killactive,
bind = $mainMod SHIFT, Q, exec, hyprctl kill
bind = $mainMod, B, exec, hyprctl dispatch "fullscreen 0 unset" && hyprctl dispatch "fullscreen 1 unset"; firefox
bind = $mainMod, slash, exec, ~/.local/bin/show-keybinds
bind = ALT, Alt_R, fullscreen, 0
bind = CTRL ALT, Z, fullscreen, 1
bind = $mainMod, F, togglefloating,
bind = $mainMod, C, centerwindow,
bind = $mainMod, D, togglesplit,
bind = $mainMod, G, togglegroup,
bind = $mainMod, W, changegroupactive,
bind = $mainMod, grave, focusurgentorlast,
bind = $mainMod, Tab, cyclenext,
bind = $mainMod SHIFT, Tab, cyclenext, prev
bind = $mainMod, period, exec, bemoji -t

# Quake terminal
bind = CTRL, grave, togglespecialworkspace, quake
bind = CTRL, grave, exec, pgrep -x "ghostty" -a | grep "quake" || ghostty --class=quake

bind = $mainMod, M, exit,
bind = $mainMod, E, exec, $fileManager
bind = $mainMod SHIFT, V, togglefloating,
bind = $mainMod, R, exec, $menu
bind = $mainMod, P, pseudo,

# Toggle status bar
bind = $mainMod SHIFT, B, exec, pkill -SIGUSR1 hyprpanel || hyprpanel

# Vim-style focus
bind = $mainMod, H, movefocus, l
bind = $mainMod, L, movefocus, r
bind = $mainMod, K, movefocus, u
bind = $mainMod, J, movefocus, d

# Vim-style window movement
bind = $mainMod SHIFT, H, movewindow, l
bind = $mainMod SHIFT, L, movewindow, r
bind = $mainMod SHIFT, K, movewindow, u
bind = $mainMod SHIFT, J, movewindow, d

# Vim-style resize
binde = $mainMod CTRL, H, resizeactive, -30 0
binde = $mainMod CTRL, L, resizeactive, 30 0
binde = $mainMod CTRL, K, resizeactive, 0 -30
binde = $mainMod CTRL, J, resizeactive, 0 30

# Workspace navigation
bind = $mainMod, bracketleft, workspace, e-1
bind = $mainMod, bracketright, workspace, e+1
bind = $mainMod SHIFT, bracketleft, movetoworkspace, e-1
bind = $mainMod SHIFT, bracketright, movetoworkspace, e+1

# Arrow key focus
bind = $mainMod, left, movefocus, l
bind = $mainMod, right, movefocus, r
bind = $mainMod, up, movefocus, u
bind = $mainMod, down, movefocus, d

# Workspaces 1-10
bind = $mainMod, 1, workspace, 1
bind = $mainMod, 2, workspace, 2
bind = $mainMod, 3, workspace, 3
bind = $mainMod, 4, workspace, 4
bind = $mainMod, 5, workspace, 5
bind = $mainMod, 6, workspace, 6
bind = $mainMod, 7, workspace, 7
bind = $mainMod, 8, workspace, 8
bind = $mainMod, 9, workspace, 9
bind = $mainMod, 0, workspace, 10

# Move to workspace
bind = $mainMod SHIFT, 1, movetoworkspace, 1
bind = $mainMod SHIFT, 2, movetoworkspace, 2
bind = $mainMod SHIFT, 3, movetoworkspace, 3
bind = $mainMod SHIFT, 4, movetoworkspace, 4
bind = $mainMod SHIFT, 5, movetoworkspace, 5
bind = $mainMod SHIFT, 6, movetoworkspace, 6
bind = $mainMod SHIFT, 7, movetoworkspace, 7
bind = $mainMod SHIFT, 8, movetoworkspace, 8
bind = $mainMod SHIFT, 9, movetoworkspace, 9
bind = $mainMod SHIFT, 0, movetoworkspace, 10

# Scratchpad
bind = $mainMod, S, togglespecialworkspace, magic
bind = $mainMod SHIFT, S, movetoworkspace, special:magic

# Mouse bindings
bind = $mainMod, mouse_down, workspace, e+1
bind = $mainMod, mouse_up, workspace, e-1
bindm = $mainMod, mouse:272, movewindow
bindm = $mainMod, mouse:273, resizewindow

# Screenshots
bind = , Print, exec, hyprshot -m output
bind = $mainMod, Print, exec, hyprshot -m window
bind = $mainMod SHIFT, Print, exec, hyprshot -m region
bind = $mainMod ALT, Print, exec, hyprshot -m region -r | satty -f -

# Clipboard history
bind = $mainMod, V, exec, cliphist list | walker --dmenu | cliphist decode | wl-copy

# Lock screen
bind = $mainMod SHIFT, L, exec, hyprlock

##############################
### WINDOWS AND WORKSPACES ###
##############################

windowrule = suppressevent maximize, class:.*
windowrule = nofocus,class:^$,title:^$,xwayland:1,floating:1,fullscreen:0,pinned:0

# Quake terminal rules
windowrule = float, class:^(quake)$
windowrule = size 100% 50%, class:^(quake)$
windowrule = move 0 0, class:^(quake)$
windowrule = animation slide, class:^(quake)$
windowrule = workspace special:quake silent, class:^(quake)$
'''

    def _get_theme_colors(self, theme: str) -> Dict[str, str]:
        """Get colors for a theme."""
        themes = {
            'catppuccin-mocha': {
                'active_border': 'rgba(cba6f7ee) rgba(89b4faee) 45deg',
                'inactive_border': 'rgba(585b70aa)',
            },
            'rose-pine': {
                'active_border': 'rgba(c4a7e7ee) rgba(ebbcbaee) 45deg',
                'inactive_border': 'rgba(6e6a86aa)',
            },
            'nord': {
                'active_border': 'rgba(88c0d0ee) rgba(81a1c1ee) 45deg',
                'inactive_border': 'rgba(4c566aaa)',
            },
        }
        return themes.get(theme, themes['catppuccin-mocha'])

    def _configure_hyprlock(self) -> bool:
        """Configure hyprlock."""
        self.logger.info("Configuring hyprlock...")

        hypr_dir = self.config_dir / 'hypr'
        config_path = hypr_dir / 'hyprlock.conf'

        config_content = '''# Hyprlock Configuration

background {
    monitor =
    path = screenshot
    blur_passes = 3
    blur_size = 8
    noise = 0.0117
    contrast = 0.8916
    brightness = 0.8172
    vibrancy = 0.1696
    vibrancy_darkness = 0.0
}

input-field {
    monitor =
    size = 200, 50
    outline_thickness = 3
    dots_size = 0.33
    dots_spacing = 0.15
    dots_center = true
    dots_rounding = -1
    outer_color = rgb(cba6f7)
    inner_color = rgb(1e1e2e)
    font_color = rgb(cdd6f4)
    fade_on_empty = true
    fade_timeout = 1000
    placeholder_text = <i>Enter Password...</i>
    hide_input = false
    rounding = 15
    check_color = rgb(a6e3a1)
    fail_color = rgb(f38ba8)
    fail_text = <i>$FAIL ($ATTEMPTS)</i>
    fail_timeout = 2000
    fail_transition = 300
    capslock_color = rgb(fab387)
    numlock_color = -1
    bothlock_color = -1
    invert_numlock = false
    swap_font_color = false
    position = 0, -20
    halign = center
    valign = center
}

label {
    monitor =
    text = $TIME
    color = rgb(cdd6f4)
    font_size = 64
    font_family = JetBrainsMono Nerd Font
    position = 0, 80
    halign = center
    valign = center
}
'''

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would write hyprlock config to {config_path}")
            return True

        config_path.write_text(config_content)
        self.logger.success(f"Created {config_path}")
        return True

    def _configure_hypridle(self) -> bool:
        """Configure hypridle."""
        self.logger.info("Configuring hypridle...")

        hypr_dir = self.config_dir / 'hypr'
        config_path = hypr_dir / 'hypridle.conf'

        config_content = '''# Hypridle Configuration

general {
    lock_cmd = pidof hyprlock || hyprlock
    before_sleep_cmd = loginctl lock-session
    after_sleep_cmd = hyprctl dispatch dpms on
}

# Dim screen after 5 minutes
listener {
    timeout = 300
    on-timeout = brightnessctl -s set 30%
    on-resume = brightnessctl -r
}

# Lock screen after 10 minutes
listener {
    timeout = 600
    on-timeout = loginctl lock-session
}

# Turn off screen after 11 minutes
listener {
    timeout = 660
    on-timeout = hyprctl dispatch dpms off
    on-resume = hyprctl dispatch dpms on
}

# Suspend after 30 minutes
listener {
    timeout = 1800
    on-timeout = systemctl suspend
}
'''

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would write hypridle config to {config_path}")
            return True

        config_path.write_text(config_content)
        self.logger.success(f"Created {config_path}")
        return True

    def _configure_panel(self) -> bool:
        """Configure HyprPanel."""
        self.logger.info("Configuring HyprPanel...")

        # HyprPanel configuration is done through its GUI
        # We just need to make sure it starts and apply a theme

        theme = self.config.get('hyprland.theme', 'catppuccin-mocha')
        theme_map = {
            'catppuccin-mocha': 'catppuccin_mocha.json',
            'rose-pine': 'rose_pine.json',
            'nord': 'nord.json',
        }
        theme_file = theme_map.get(theme, 'catppuccin_mocha.json')

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would apply HyprPanel theme: {theme_file}")
            return True

        # Apply theme via CLI if possible
        theme_path = self.config_dir / 'ags' / 'themes' / theme_file
        if theme_path.exists():
            result = self.cmd.run_quiet(['hyprpanel', 'ut', str(theme_path)])
            if result.success:
                self.logger.success(f"Applied HyprPanel theme: {theme}")
            else:
                self.logger.warning("Could not apply HyprPanel theme")
        else:
            self.logger.info("HyprPanel theme will be configured through GUI")

        return True

    def _configure_launcher(self) -> bool:
        """Configure Walker launcher."""
        self.logger.info("Configuring Walker launcher...")

        walker_dir = self.config_dir / 'walker'
        walker_dir.mkdir(parents=True, exist_ok=True)

        # Copy default config if available
        default_config = Path('/etc/xdg/walker/config.toml')
        if default_config.exists():
            config_path = walker_dir / 'config.toml'

            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would copy Walker config to {config_path}")
                return True

            shutil.copy(default_config, config_path)

            # Copy themes too
            default_themes = Path('/etc/xdg/walker/themes')
            if default_themes.exists():
                dest_themes = walker_dir / 'themes'
                if dest_themes.exists():
                    shutil.rmtree(dest_themes)
                shutil.copytree(default_themes, dest_themes)

            self.logger.success("Walker configuration copied")
        else:
            self.logger.info("Walker will use default configuration")

        return True

    def _create_keybinds_helper(self) -> bool:
        """Create keybindings helper script."""
        self.logger.info("Creating keybindings helper...")

        bin_dir = self.home / '.local' / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)

        script_path = bin_dir / 'show-keybinds'

        script_content = r'''#!/bin/bash
# Show keybindings in a popup using walker

keybinds="=== APPS ===
SUPER + T : Terminal
SUPER + B : Firefox
SUPER + E : File manager (Nemo)
SUPER + R : App launcher (Walker)
SUPER + V : Clipboard history
SUPER + . : Emoji picker
SUPER + / : This help
CTRL + \` : Quake terminal
---
=== WINDOWS ===
SUPER + Q : Close window
SUPER + SHIFT + Q : Force kill window
SUPER + F : Toggle floating
SUPER + C : Center floating window
SUPER + Tab : Cycle windows
SUPER + \` : Focus urgent window
LALT + RALT : Toggle fullscreen
CTRL + ALT + Z : Maximize (keep bar)
---
=== VIM MOVEMENT ===
SUPER + HJKL : Move focus
SUPER + SHIFT + HJKL : Move window
SUPER + CTRL + HJKL : Resize window
SUPER + Arrows : Move focus (alt)
---
=== LAYOUT ===
SUPER + D : Toggle split direction
SUPER + P : Pseudo tile
SUPER + G : Toggle group/tabs
SUPER + W : Cycle grouped windows
---
=== WORKSPACES ===
SUPER + 1-0 : Switch workspace
SUPER + SHIFT + 1-0 : Move window to workspace
SUPER + [ : Previous workspace
SUPER + ] : Next workspace
SUPER + SHIFT + [ : Move window to prev WS
SUPER + SHIFT + ] : Move window to next WS
SUPER + S : Scratchpad
SUPER + SHIFT + S : Move to scratchpad
SUPER + Scroll : Cycle workspaces
---
=== MOUSE ===
SUPER + LMB drag : Move window
SUPER + RMB drag : Resize window
---
=== SYSTEM ===
SUPER + SHIFT + L : Lock screen
SUPER + SHIFT + B : Toggle status bar
SUPER + M : Exit Hyprland
---
=== SCREENSHOT ===
Print : Full screen
SUPER + Print : Window
SUPER + SHIFT + Print : Region
SUPER + ALT + Print : Region + annotate"

echo "$keybinds" | walker --dmenu -p "Keybindings"
'''

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would create keybinds helper at {script_path}")
            return True

        script_path.write_text(script_content)
        script_path.chmod(0o755)
        self.logger.success(f"Created {script_path}")
        return True
