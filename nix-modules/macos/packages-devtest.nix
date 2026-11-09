# Test targets for web, mobile and native work: browser engines, simulator
# tooling, Linux/macOS VMs. Laptop only: the desktop is SSH-only.
# Simulator runtimes are not brew packages: `xcodebuild -downloadPlatform iOS` fetches them.
{ ... }:
{
  homebrew = {
    enable = true;
    brews = [
      "xcodes" # install/switch Xcode versions and simulator runtimes
      "xcbeautify" # readable xcodebuild test output
      "swiftlint"
      "swiftformat"
      "ninja" # Linux/macOS native builds (cmake is in packages-tui.nix)
      "meson"
      "mkcert" # trusted local HTTPS, for testing on simulators and devices
    ];
    casks = [
      "utm" # Linux VMs (arm64 native, x86_64 via QEMU/Rosetta) and macOS guests
    ];
  };
}
