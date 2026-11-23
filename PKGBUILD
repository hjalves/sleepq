# Local package: build with `makepkg -si` from this directory.
pkgname=sleepq
pkgver=0.1.0
pkgrel=6
pkgdesc="Wake on RTC alarm, run tasks queued in a git repo, then suspend again"
arch=('any')
license=('MIT')
depends=('python>=3.11' 'systemd' 'util-linux' 'git' 'bash')
backup=('etc/sleepq/config.toml')
install=sleepq.install
source=('sleepq'
        'sleepq.service'
        'sleepq-web.service'
        'sleepq.sleep-hook'
        'sleepq.tmpfiles'
        'config.toml'
        'README.md')
sha256sums=('de72304ca971ae59161861b586d968e10b2e610ad95f2312c95a68af880da930'
            '867b079b83c1a8a656f1f054326c811f1378637b7135139247d7d07cf09bce4c'
            '482811833b501e4f19306a90bb37c080ffbb29935b67f900efc156c2e2d70047'
            '2a51bc7d5b064aead6175a3e13e2ef49e2aab159c3a5532f5f2614e3b2424cc8'
            '81493360677d8375d5d329850b3032a6ba648ac190e8bb13629b7247ee284ab1'
            '0578d5dd724635a03fdcb930539ca3261af9e1e88c9f8ffa22547f50a5c96d1c'
            'b341b58bd97526215fcac245a43e94ecbb82dd5c142250b9ba4d33004290f16e')

package() {
  install -Dm755 sleepq             "$pkgdir/usr/bin/sleepq"
  install -Dm644 sleepq.service     "$pkgdir/usr/lib/systemd/system/sleepq.service"
  install -Dm644 sleepq-web.service "$pkgdir/usr/lib/systemd/system/sleepq-web.service"
  install -Dm755 sleepq.sleep-hook  "$pkgdir/usr/lib/systemd/system-sleep/sleepq"
  install -Dm644 sleepq.tmpfiles    "$pkgdir/usr/lib/tmpfiles.d/sleepq.conf"
  install -Dm644 config.toml        "$pkgdir/etc/sleepq/config.toml"
  install -Dm644 README.md          "$pkgdir/usr/share/doc/sleepq/README.md"
}
