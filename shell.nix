{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python312
    pkgs.fish
    pkgs.podman-compose
  ];

  shellHook = ''
    exec fish
  '';
}
