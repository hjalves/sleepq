# Local package: build with `makepkg -si` from this directory.
pkgname=sleepq
pkgver=0.1.0
pkgrel=3
pkgdesc="Wake on RTC alarm, run tasks queued in a git repo, then suspend again"
arch=('any')
license=('MIT')
depends=('python>=3.11' 'systemd' 'util-linux' 'git' 'bash')
backup=('etc/sleepq/config.toml')
install=sleepq.install
source=('sleepq'
        'sleepq.service'
        'sleepq.sleep-hook'
        'sleepq.tmpfiles'
        'config.toml'
        'README.md')
sha256sums=('739e2d40077621b77efff487eadea8494412f17a24f99ed19e0927ad095a2bda'
            '867b079b83c1a8a656f1f054326c811f1378637b7135139247d7d07cf09bce4c'
            '2a51bc7d5b064aead6175a3e13e2ef49e2aab159c3a5532f5f2614e3b2424cc8'
            '81493360677d8375d5d329850b3032a6ba648ac190e8bb13629b7247ee284ab1'
            'e3423f790dde98317a2f2594e969d3c0e4f0d5eac91b66e52e40194f7abee1c7'
            '67a022ec6a1c461e301920b503978ba3c4cc585c20730931bd7228b853366239')

package() {
  install -Dm755 sleepq             "$pkgdir/usr/bin/sleepq"
  install -Dm644 sleepq.service     "$pkgdir/usr/lib/systemd/system/sleepq.service"
  install -Dm755 sleepq.sleep-hook  "$pkgdir/usr/lib/systemd/system-sleep/sleepq"
  install -Dm644 sleepq.tmpfiles    "$pkgdir/usr/lib/tmpfiles.d/sleepq.conf"
  install -Dm644 config.toml        "$pkgdir/etc/sleepq/config.toml"
  install -Dm644 README.md          "$pkgdir/usr/share/doc/sleepq/README.md"
}
