# Local package: build with `makepkg -si` from this directory.
pkgname=sleepq
pkgver=0.1.0
pkgrel=7
pkgdesc="Wake on RTC alarm, run tasks queued in a git repo, then suspend again"
arch=('any')
license=('MIT')
depends=('python>=3.11' 'systemd' 'util-linux' 'git' 'bash')
optdepends=('python-pystray: sleepq-tray system tray icon')
backup=('etc/sleepq/config.toml')
install=sleepq.install
source=('sleepq'
        'sleepq.service'
        'sleepq-web.service'
        'sleepq.sleep-hook'
        'sleepq.tmpfiles'
        'config.toml'
        'README.md'
        'sleepq-tray'
        'sleepq-tray.desktop')
sha256sums=('de72304ca971ae59161861b586d968e10b2e610ad95f2312c95a68af880da930'
            '867b079b83c1a8a656f1f054326c811f1378637b7135139247d7d07cf09bce4c'
            '482811833b501e4f19306a90bb37c080ffbb29935b67f900efc156c2e2d70047'
            '2a51bc7d5b064aead6175a3e13e2ef49e2aab159c3a5532f5f2614e3b2424cc8'
            '81493360677d8375d5d329850b3032a6ba648ac190e8bb13629b7247ee284ab1'
            '0578d5dd724635a03fdcb930539ca3261af9e1e88c9f8ffa22547f50a5c96d1c'
            '8490b7c21f5418c9461b33a6c014879ffef6829ca6b315828f0259fb7243c209'
            '59839424b38b587d4ac9a27d73d867c093a569c5a718d65817d814b86ec44d05'
            '9514aa8d87a39f96004d761e0b8b00726ff4a46ccfb673c8b23be0472df0bfc6')

package() {
  install -Dm755 sleepq             "$pkgdir/usr/bin/sleepq"
  install -Dm644 sleepq.service     "$pkgdir/usr/lib/systemd/system/sleepq.service"
  install -Dm644 sleepq-web.service "$pkgdir/usr/lib/systemd/system/sleepq-web.service"
  install -Dm755 sleepq.sleep-hook  "$pkgdir/usr/lib/systemd/system-sleep/sleepq"
  install -Dm644 sleepq.tmpfiles    "$pkgdir/usr/lib/tmpfiles.d/sleepq.conf"
  install -Dm644 config.toml        "$pkgdir/etc/sleepq/config.toml"
  install -Dm644 README.md          "$pkgdir/usr/share/doc/sleepq/README.md"
  install -Dm755 sleepq-tray        "$pkgdir/usr/bin/sleepq-tray"
  install -Dm644 sleepq-tray.desktop "$pkgdir/usr/share/applications/sleepq-tray.desktop"
  install -Dm644 sleepq-tray.desktop "$pkgdir/etc/xdg/autostart/sleepq-tray.desktop"
}
