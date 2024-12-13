{
  launchd.jobs.stats = {
    enable = true;
    program = "/Applications/Stats.app/Contents/MacOS/Stats";
    runAtLoad = true;
    keepAlive = true;
    environment = {
      PATH = "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin";
    };
  };
}
