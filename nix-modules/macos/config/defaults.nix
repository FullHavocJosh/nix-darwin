{ ... }:
{
  system.defaults = {
    NSGlobalDomain.AppleInterfaceStyle = "Dark";
    NSGlobalDomain.AppleIconAppearanceTheme = null;
    NSGlobalDomain.NSScrollAnimationEnabled = true;
    NSGlobalDomain.NSWindowResizeTime = 0.05;

    dock.autohide = true;
    dock.autohide-delay = 0.5;
    dock.autohide-time-modifier = 0.5;
    dock.tilesize = 32;
    dock.largesize = 64;
    dock.magnification = true;
    dock.mineffect = "genie";
    dock.mru-spaces = false;
    dock.showhidden = true;
    dock.launchanim = true;
    dock.orientation = "bottom";
    dock.static-only = false;
    dock.show-recents = false;
    dock.slow-motion-allowed = false;
    dock.dashboard-in-overlay = true;
    dock.expose-group-apps = true;
    dock.expose-animation-duration = 0.05;
    dock.minimize-to-application = false;
    dock.wvous-bl-corner = 1;
    dock.wvous-br-corner = 1;
    dock.wvous-tl-corner = 1;
    dock.wvous-tr-corner = 1;
    dock.show-process-indicators = true;
    dock.appswitcher-all-displays = false;
    dock.scroll-to-open = false;
    dock.mouse-over-hilite-stack = true;

    NSGlobalDomain._HIHideMenuBar = false;
    menuExtraClock.IsAnalog = false;
    menuExtraClock.ShowAMPM = false;
    menuExtraClock.ShowDate = 0;
    menuExtraClock.Show24Hour = false;
    menuExtraClock.ShowSeconds = false;
    menuExtraClock.ShowDayOfWeek = false;
    menuExtraClock.ShowDayOfMonth = false;
    menuExtraClock.FlashDateSeparators = false;

    finder.ShowPathbar = true;
    finder.ShowStatusBar = true;
    finder.AppleShowAllFiles = true;
    finder.AppleShowAllExtensions = true;
    finder.FXPreferredViewStyle = "Nlsv";
    finder.FXDefaultSearchScope = "SCcf";
    finder.FXEnableExtensionChangeWarning = false;
    finder._FXSortFoldersFirst = true;
    finder._FXSortFoldersFirstOnDesktop = true;
    finder._FXShowPosixPathInTitle = true;
    finder._FXEnableColumnAutoSizing = false;
    finder.QuitMenuItem = false;
    finder.CreateDesktop = false;
    finder.FXRemoveOldTrashItems = false;
    finder.NewWindowTarget = "iCloud Drive";
    finder.ShowExternalHardDrivesOnDesktop = false;
    finder.ShowHardDrivesOnDesktop = false;
    finder.ShowRemovableMediaOnDesktop = false;
    finder.ShowMountedServersOnDesktop = false;
    NSGlobalDomain.AppleShowAllFiles = true;
    NSGlobalDomain.AppleShowAllExtensions = true;

    loginwindow.GuestEnabled = false;

    trackpad.Clicking = false;
    trackpad.Dragging = false;
    trackpad.TrackpadRightClick = true;
    trackpad.TrackpadThreeFingerDrag = false;
    trackpad.TrackpadMomentumScroll = true;
    trackpad.TrackpadPinch = true;
    trackpad.TrackpadRotate = false;
    trackpad.TrackpadTwoFingerDoubleTapGesture = false;
    trackpad.TrackpadFourFingerHorizSwipeGesture = 0;
    trackpad.TrackpadFourFingerVertSwipeGesture = 0;
    trackpad.TrackpadFourFingerPinchGesture = 0;
    trackpad.DragLock = false;
    trackpad.TrackpadThreeFingerHorizSwipeGesture = 0;
    trackpad.TrackpadThreeFingerVertSwipeGesture = 0;
    trackpad.TrackpadTwoFingerFromRightEdgeSwipeGesture = 3;
    trackpad.TrackpadThreeFingerTapGesture = 0;
    trackpad.TrackpadCornerSecondaryClick = 0;
    trackpad.FirstClickThreshold = 1;
    trackpad.SecondClickThreshold = 1;
    trackpad.ActuateDetents = true;
    NSGlobalDomain.AppleEnableSwipeNavigateWithScrolls = false;
    NSGlobalDomain.NSWindowShouldDragOnGesture = true;

    NSGlobalDomain."com.apple.keyboard.fnState" = false;
    NSGlobalDomain.KeyRepeat = 2;
    NSGlobalDomain.InitialKeyRepeat = 15;
    hitoolbox.AppleFnUsageType = "Do Nothing";

    WindowManager.AutoHide = true;
    WindowManager.StandardHideDesktopIcons = true;
    WindowManager.HideDesktop = true;
    WindowManager.EnableStandardClickToShowDesktop = false;
    WindowManager.GloballyEnabled = false;
    WindowManager.AppWindowGroupingBehavior = false;
    WindowManager.EnableTilingByEdgeDrag = true;
    WindowManager.EnableTopTilingByEdgeDrag = true;
    WindowManager.EnableTilingOptionAccelerator = true;
    WindowManager.EnableTiledWindowMargins = true;
    WindowManager.StandardHideWidgets = false;
    WindowManager.StageManagerHideWidgets = false;

    NSGlobalDomain.ApplePressAndHoldEnabled = false;
    NSGlobalDomain.NSDocumentSaveNewDocumentsToCloud = true;
    NSGlobalDomain.NSAutomaticInlinePredictionEnabled = false;
    NSGlobalDomain.NSAutomaticSpellingCorrectionEnabled = false;
    NSGlobalDomain.NSAutomaticPeriodSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticCapitalizationEnabled = false;
    NSGlobalDomain.NSAutomaticDashSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticQuoteSubstitutionEnabled = false;
    NSGlobalDomain.AppleScrollerPagingBehavior = true;
    NSGlobalDomain.AppleShowScrollBars = "Automatic";
    NSGlobalDomain."com.apple.swipescrolldirection" = true;
    NSGlobalDomain."com.apple.sound.beep.volume" = 0.4346;

    screensaver.askForPassword = true;
    screensaver.askForPasswordDelay = 0;

    screencapture.type = "png";
    screencapture.disable-shadow = false;
    screencapture.include-date = true;
    screencapture.save-selections = true;
    screencapture.show-thumbnail = true;
    screencapture.target = "file";

    spaces.spans-displays = false;
    SoftwareUpdate.AutomaticallyInstallMacOSUpdates = false;
    LaunchServices.LSQuarantine = true;
    magicmouse.MouseButtonMode = "TwoButton";
  };
}
