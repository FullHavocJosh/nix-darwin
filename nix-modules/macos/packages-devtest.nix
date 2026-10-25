# Test targets for web, mobile and native work: browser engines, simulator
# tooling, Linux/macOS VMs. Laptop only: the desktop is SSH-only.
# Android Studio, the Android SDK tools and temurin are in packages-tui.nix.
# Simulator runtimes and Android system images are not brew packages:
# `xcodebuild -downloadPlatform iOS` and `sdkmanager` fetch them.
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
      "firefox" # Gecko
      "firefox@developer-edition"
      "google-chrome" # Blink as users run it (ungoogled-chromium lacks Google services)
      "safari-technology-preview" # next WebKit
      "temurin@21" # LTS JDK for command-line Gradle; temurin (27) is newer than AGP expects
      "utm" # Linux VMs (arm64 native, x86_64 via QEMU/Rosetta) and macOS guests
    ];
  };
}
