{ pkgs, lib, ... }:
  let
    # Reusable function for package installation
    installPackages = { manager, installCmd, listCmd, checkCmd, packages }: lib.concatStringsSep "\n" (map (pkg: ''
      if ! ${checkCmd} ${pkg} &> /dev/null; then
        echo "Installing ${pkg}..."
        ${installCmd} ${pkg}
      else
        echo "${pkg} is already installed."
      fi
    '') packages);

    # Package lists
    brewPackages = [
      "ansible"
      "ansible-lint"
      "cmake"
      "fastfetch"
      "go"
      "luarocks"
      "neovim"
      "oh-my-posh"
      "prettier"
      "syncthing"
      "rust"
      "telnet"
      "tmux"
      "tmuxinator"
      "tmuxinator-completion"
      "tpm"
      "watch"
      "bash-language-server"
      "lua-language-server"
      "yaml-language-server"
      "atuin"
      "zplug"
    ];

    dnfPackages = [
      "alacritty"
      "btop"
      "git"
      "neovim"
      "vlc"
    ];

    flatpakApps = [
      "com.discordapp.Discord"
      "com.jetbrains.GoLand"
    ];
  in {
    # Ensure Linuxbrew is installed
    home.activation.installLinuxbrew = lib.mkAfter ''
      echo "Installing Linuxbrew..."
      if [ ! -d "/home/linuxbrew/.linuxbrew" ]; then
        sudo dnf groupinstall -y "Development Tools"
        sudo dnf install -y curl file git
        bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo "Linuxbrew installation complete."
      else
        echo "Linuxbrew is already installed."
      fi
    '';

    # Linuxbrew activation script
    home.activation.linuxbrewPackages = lib.mkAfter ''
      echo "Initializing Linuxbrew environment..."
      eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
      brew update

      echo "Installing Linuxbrew packages..."
      ${installPackages {
        manager = "brew";
        installCmd = "brew install";
        listCmd = "brew list --formula";
        checkCmd = "grep -q";
        packages = brewPackages;
      }}

      echo "Linuxbrew packages installed successfully."
    '';

    # DNF activation script
    home.activation.dnfPackages = lib.mkAfter ''
      echo "Setting up DNF packages..."

      # Update DNF cache
      echo "Updating DNF cache..."
      sudo dnf makecache -y

      ${installPackages {
        manager = "dnf";
        installCmd = "sudo dnf install -y";
        listCmd = "rpm -q";
        checkCmd = "";
        packages = dnfPackages;
      }}

      echo "DNF package setup complete."
    '';

    # Flatpak activation script
    home.activation.flatpakPackages = lib.mkAfter ''
      echo "Setting up Flatpak..."
      # Ensure Flatpak is installed
      if ! command -v flatpak &> /dev/null; then
        echo "Flatpak is not installed. Installing it..."
        sudo dnf install -y flatpak
      fi

      # Add Flathub repository if not already added
      if ! flatpak remotes | grep -q "flathub"; then
        echo "Adding Flathub repository..."
        flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
      fi

      ${installPackages {
        manager = "flatpak";
        installCmd = "flatpak install -y flathub";
        listCmd = "flatpak list";
        checkCmd = "grep -q";
        packages = flatpakApps;
      }}

      echo "Flatpak setup complete."
    '';
  }
