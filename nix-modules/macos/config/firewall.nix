{ ... }:
{
  networking.applicationFirewall = {
    enable = false;
    allowSigned = true;
    allowSignedApp = true;
    enableStealthMode = false;
    blockAllIncoming = false;
  };
}
