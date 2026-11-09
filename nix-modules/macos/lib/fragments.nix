# Reads shell files into Nix strings, so long activation scripts live in .sh files.
# file: one file; dir: every file of a directory, joined in name order. @name@ placeholders
# become the values in subs, which is how a script gets a store path or the user name.
{ lib }:
let
  substitute =
    subs: text:
    lib.replaceStrings (map (n: "@${n}@") (builtins.attrNames subs)) (builtins.attrValues subs) text;
in
{
  file = path: subs: substitute subs (builtins.readFile path);

  dir =
    path: subs:
    lib.concatMapStrings (name: substitute subs (builtins.readFile (path + "/${name}"))) (
      lib.sort builtins.lessThan (builtins.attrNames (builtins.readDir path))
    );
}
