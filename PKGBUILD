# Local package: build with `makepkg -si` from this directory.
pkgname=sleepq
pkgver=0.1.0
pkgrel=4
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
sha256sums=('3a1cd72a66ab555ca018a653623b20b4bd15f70dccc96d3dd72c14b13bd978df'
            '867b079b83c1a8a656f1f054326c811f1378637b7135139247d7d07cf09bce4c'
            '2a51bc7d5b064aead6175a3e13e2ef49e2aab159c3a5532f5f2614e3b2424cc8'
            '81493360677d8375d5d329850b3032a6ba648ac190e8bb13629b7247ee284ab1'
            '8332c9650c8c24ccf6e81c71df323a1193e9164ae4df43a375cc8bfba76724f9'
            '569ff263bbcf664693818faa727bb236ce5c0085f685f15d6196a4e00f9804fa')

package() {
  install -Dm755 sleepq             "$pkgdir/usr/bin/sleepq"
  install -Dm644 sleepq.service     "$pkgdir/usr/lib/systemd/system/sleepq.service"
  install -Dm755 sleepq.sleep-hook  "$pkgdir/usr/lib/systemd/system-sleep/sleepq"
  install -Dm644 sleepq.tmpfiles    "$pkgdir/usr/lib/tmpfiles.d/sleepq.conf"
  install -Dm644 config.toml        "$pkgdir/etc/sleepq/config.toml"
  install -Dm644 README.md          "$pkgdir/usr/share/doc/sleepq/README.md"
}
