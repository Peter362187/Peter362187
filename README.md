<!--
  ┌──────────────────────────────────────────────────────────────────┐
  │  Du liest den Quelltext eines README.                            │
  │  Das ist entweder Neugier oder OPSEC. Beides wird akzeptiert.    │
  │                                                                  │
  │  $ cat .secret                                                   │
  │  L4RP was here.                                                  │
  │                                                                  │
  │  Die Terminals sind generiert, nicht handgeschrieben:            │
  │      python tools/gen_terminal_svg.py                            │
  │  Text aendern -> in tools/gen_terminal_svg.py bei SCENES.        │
  └──────────────────────────────────────────────────────────────────┘
-->

<p align="center">
  <img src="assets/hero.svg" width="753"
       alt="L4RP - arch linux tooling, python, opsec enabled">
</p>

<p align="center">
  <img src="assets/header.svg" width="753"
       alt="user@github:~$ whoami — L4RP. SYSTEM STATUS: ONLINE, OPSEC: ENABLED, GIT: CLEAN.">
</p>

<img src="assets/divider.svg" width="753" alt="">

## `// 01` whoami

```
NAME     : L4RP
ROLE     : builds things that boot
DISTRO   : Arch Linux (yes, that is a personality trait)
LANG     : Python, Shell, a regrettable amount of Batch
DOING    : turning "just install Arch" into a wizard anyone can click
DEBUG    : print statements, exclusively
TESTING  : ship it, the users will find them
STATUS   : it compiled, therefore it works
CONTACT  : open an issue, that is what they are for
```

I mostly build tooling — the boring layer between "this is possible" and
"a normal person can actually do it". Currently that means packaging Arch
Linux into something you can hand to someone without a two-hour phone call.

<img src="assets/divider.svg" width="753" alt="">

## `// 02` stack

<p align="center">
  <img src="assets/stack.svg" width="753"
       alt="user@github:~$ neofetch — os: Arch Linux, shell: bash, lang: Python, Shell, Batch.">
</p>

```
drwxr-xr-x  l4rp  python      main driver — CLI, GUI, build pipelines
drwxr-xr-x  l4rp  bash        glue, installers, anything with a shebang
drwxr-xr-x  l4rp  linux       arch, systemd, squashfs, mkinitcpio
drwxr-xr-x  l4rp  windows     WSL bridges, batch launchers, PowerShell
drwxr-xr-x  l4rp  git         branches are cheap, force-push is not
-rwxr-xr-x  l4rp  stackover~  copy-paste, attribution optional
-rw-r--r--  l4rp  docs        planned. always planned.
-rw-------  root  opsec       permission denied
```

<img src="assets/divider.svg" width="753" alt="">

## `// 03` daemons

<p align="center">
  <img src="assets/services.svg" width="753"
       alt="systemctl status motivation — active (running). systemctl status hypergamie. sudo rm -rf /doubt.">
</p>

<p align="center">
  <img src="assets/lonely.svg" width="753"
       alt="find / -name girlfriend — keine Treffer, reason: hypergamie.service haelt alle Referenzen. Danach apt install being-funny, das stattdessen jawline, filler und height-booster einrichtet; Personality: unchanged.">
</p>

<img src="assets/divider.svg" width="753" alt="">

## `// 04` review

<p align="center">
  <img src="assets/review.svg" width="753"
       alt="git push origin main - remote error: refusing to push, reason: the code is ass. Auch git push --force wird abgelehnt: it is still ass, no.">
</p>

<img src="assets/divider.svg" width="753" alt="">

## `// 05` telemetry

<p align="center">
  <img src="assets/stats.svg" width="753"
       alt="Repo-, Follower- und Sprachstatistik als Terminal-Ausgabe.">
</p>

<sub>Selbst erzeugt aus der GitHub-API — kein externer Badge-Dienst, der
ausfallen kann. Aktualisiert sich woechentlich per Action.</sub>

<img src="assets/divider.svg" width="753" alt="">

## `// 06` payloads

<p align="center">
  <img src="assets/payloads.svg" width="753"
       alt="gh repo list zeigt Easy-Arch-Linux (Python, 1 Stern); gh repo view zeigt Beschreibung, Topics und Adresse.">
</p>

<sub>Aus der GitHub-API erzeugt — die Liste bleibt aktuell, ohne dass ich
sie hier von Hand nachpflege.</sub>

<img src="assets/divider.svg" width="753" alt="">

<p align="center">
  <img src="assets/footer.svg" width="753"
       alt="user@github:~$ exit - Connection to localhost closed.">
</p>

<!--
  Noch hier? Dann verdienst du das hier:

      $ echo $?
      0

  Alles in Ordnung. Immer gewesen.
-->
