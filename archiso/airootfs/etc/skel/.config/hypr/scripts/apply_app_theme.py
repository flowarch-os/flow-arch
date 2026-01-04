import sys
import os
import subprocess
from pathlib import Path

def run_cmd(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e}")


def apply_gtk(bg, fg):
    # 1. Setup Unique Theme Name
    theme_name = f"HyprTheme_{bg}_{fg}"
    home = Path.home()
    
    # Use standard XDG path
    themes_root = home / ".local/share/themes"
    themes_root.mkdir(parents=True, exist_ok=True)

    # 2. Clean up old generated themes to prevent clutter
    import shutil
    for item in themes_root.iterdir():
        if item.is_dir() and item.name.startswith("HyprTheme") and item.name != theme_name:
            try:
                shutil.rmtree(item)
            except OSError:
                pass

def apply_gtk(bg, fg):
    home = Path.home()
    config_dir = home / ".config"
    settings_ini = config_dir / "gtk-3.0/settings.ini"
    
    # 1. Determine A/B Target
    current_theme = ""
    if settings_ini.exists():
        try:
            with open(settings_ini, "r") as f:
                for line in f:
                    if "gtk-theme-name=" in line:
                        current_theme = line.split("=")[1].strip()
                        break
        except Exception:
            pass

    # Toggle logic: If A -> B, otherwise -> A
    if current_theme == "HyprTheme_A":
        theme_name = "HyprTheme_B"
    else:
        theme_name = "HyprTheme_A"
    
    # We will write to both legacy and modern paths to ensure everything finds it
    legacy_themes = home / ".themes"
    modern_themes = home / ".local/share/themes"
    
    # 2. Clean up old/timestamped themes and the OTHER toggle
    # If we are switching to A, remove B (and vice versa) to be clean
    import shutil
    
    themes_to_remove = ["HyprTheme", "HyprTheme_A", "HyprTheme_B"] 
    # Don't remove the one we are about to create
    if theme_name in themes_to_remove:
        themes_to_remove.remove(theme_name)

    for root in [legacy_themes, modern_themes]:
        if root.exists():
            for item in root.iterdir():
                # Clean up random timestamped ones
                if item.is_dir() and item.name.startswith("HyprTheme_") and item.name not in ["HyprTheme_A", "HyprTheme_B"]:
                    try:
                        shutil.rmtree(item)
                    except OSError:
                        pass
                # Clean up the toggle we are swapping AWAY from
                if item.is_dir() and item.name in themes_to_remove:
                    try:
                        shutil.rmtree(item)
                    except OSError:
                        pass

    # 3. Create New Theme Directories
    for root in [legacy_themes, modern_themes]:
        root.mkdir(parents=True, exist_ok=True)
        theme_dir = root / theme_name
        theme_dir.mkdir(exist_ok=True)
        (theme_dir / "gtk-3.0").mkdir(parents=True, exist_ok=True)
        (theme_dir / "gtk-4.0").mkdir(parents=True, exist_ok=True)

        # 4. Generate CSS Content (Strong Selectors)
        css_content = f"""
/* Custom Generated Theme: {theme_name} */
@define-color accent_color #{fg};
@define-color accent_bg_color #{fg};
@define-color accent_fg_color #{bg};
@define-color window_bg_color #{bg};
@define-color window_fg_color #ffffff;
@define-color view_bg_color #{bg};
@define-color view_fg_color #ffffff;
@define-color headerbar_bg_color #{bg};
@define-color headerbar_fg_color #{fg};
@define-color headerbar_border_color #{fg};
@define-color headerbar_backdrop_color @window_bg_color;
@define-color card_bg_color shade(#{bg}, 1.05);
@define-color card_fg_color #ffffff;
@define-color popover_bg_color shade(#{bg}, 1.1);
@define-color popover_fg_color #ffffff;

/* Standard GTK named colors */
@define-color theme_bg_color #{bg};
@define-color theme_fg_color #{fg};
@define-color theme_selected_bg_color #{fg};
@define-color theme_selected_fg_color #{bg};

/* Base overrides */
window,
.background,
.view,
.adw-window,
decoration,
decoration-overlay {{
    background-color: #{bg};
    color: #ffffff;
}}

/* Headerbars */
headerbar {{
    background-color: #{bg};
    color: #{fg};
    border-bottom: 1px solid #{fg};
}}

headerbar button {{
    color: #{fg};
}}

/* Sidebar */
.sidebar, stacksidebar, list, treeview {{
    background-color: shade(#{bg}, 0.95);
    color: #ffffff;
}}

/* Inputs */
entry, textview {{
    background-color: shade(#{bg}, 0.9);
    color: #ffffff;
    border: 1px solid #{fg};
}}

/* Buttons */
button {{
    background-color: shade(#{bg}, 1.1);
    color: #ffffff;
    border: 1px solid #{fg};
}}

button:hover {{
    background-color: #{fg};
    color: #{bg};
}}

/* Selection */
selection {{
    background-color: #{fg};
    color: #{bg};
}}
"""
        
        # 5. Write CSS to Theme Folder
        with open(theme_dir / "gtk-3.0/gtk.css", "w") as f:
            f.write(css_content)
        with open(theme_dir / "gtk-4.0/gtk.css", "w") as f:
            f.write(css_content)

        # 6. Create index.theme
        index_content = f"""[Desktop Entry]
Type=X-GNOME-Metatheme
Name={theme_name}
Comment=Dynamically generated theme
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme={theme_name}
Metatheme={theme_name}
IconTheme=Adwaita
CursorTheme=Adwaita
"""
        with open(theme_dir / "index.theme", "w") as f:
            f.write(index_content)

    # 7. Update settings.ini to point to New Theme
    config_dir = home / ".config"
    settings_content = f"""[Settings]
gtk-application-prefer-dark-theme=1
gtk-theme-name={theme_name}
gtk-icon-theme-name=Adwaita
"""
    with open(config_dir / "gtk-3.0/settings.ini", "w") as f:
        f.write(settings_content)
    with open(config_dir / "gtk-4.0/settings.ini", "w") as f:
        f.write(settings_content)

    # 8. Update xsettingsd configuration
    xsettings_dir = config_dir / "xsettingsd"
    xsettings_dir.mkdir(exist_ok=True)
    xsettings_conf = xsettings_dir / "xsettingsd.conf"
    
    xsettings_content = f"""Net/ThemeName "{theme_name}"
Net/IconThemeName "Adwaita"
Gtk/CursorThemeName "Adwaita"
Net/EnableEventSounds 0
"""
    with open(xsettings_conf, "w") as f:
        f.write(xsettings_content)
        
    # 9. Reload or Start xsettingsd
    try:
        # Check if running
        pid = subprocess.check_output(["pgrep", "xsettingsd"]).decode().strip()
        # Send SIGHUP to reload
        subprocess.run(["kill", "-1", pid])
    except subprocess.CalledProcessError:
        # Not running, start it
        subprocess.Popen(["xsettingsd"])

    # 10. Apply via GSettings
    run_cmd(f"gsettings set org.gnome.desktop.interface gtk-theme '{theme_name}'")
    run_cmd("gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'")

def apply_qt(bg, fg):
    # Update Qt5ct/Qt6ct to use a generated QSS
    qss_content = f"""
QWidget {{
    background-color: #{bg};
    color: #ffffff;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QAbstractItemView {{
    background-color: #{bg};
    color: #ffffff;
    border: 1px solid #{fg};
    selection-background-color: #{fg};
    selection-color: #{bg};
}}
QListView, QTreeView, QTableView {{
    background-color: #{bg};
    alternate-background-color: #{bg};
}}
QListView::item:selected, QTreeView::item:selected {{
    background-color: #{fg};
    color: #{bg};
}}
QPushButton {{
    background-color: #{bg};
    color: #ffffff;
    border: 1px solid #{fg};
    padding: 4px;
}}
QPushButton:hover {{
    background-color: #{fg};
    color: #{bg};
}}
QMenu {{
    background-color: #{bg};
    color: #ffffff;
    border: 1px solid #{fg};
}}
QMenu::item:selected {{
    background-color: #{fg};
    color: #{bg};
}}
"""
    for qt_ver in ["qt5ct", "qt6ct"]:
        config_dir = Path.home() / f".config/{qt_ver}"
        qss_dir = config_dir / "qss"
        qss_dir.mkdir(parents=True, exist_ok=True)
        
        with open(qss_dir / "HyprTheme.qss", "w") as f:
            f.write(qss_content)
            
        conf_content = f"""[Appearance]
style_sheet=HyprTheme.qss
custom_palette=false
style=Fusion
icon_theme=Adwaita
standard_dialogs=default
"""
        with open(config_dir / f"{qt_ver}.conf", "w") as f:
            f.write(conf_content)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python3 apply_app_theme.py <bg_hex> <fg_hex>")
        sys.exit(1)
        
    bg = sys.argv[1]
    fg = sys.argv[2]
    
    apply_gtk(bg, fg)
    apply_qt(bg, fg)
