#!/usr/bin/env bash
# 装 dev-browser 及其 Playwright 浏览器, 可重复执行.
#
# 官方流程是 `npm install -g dev-browser && dev-browser install`, 实际有两个坑:
# 1. npm 11+ 默认拦截 install script, 下原生二进制的 postinstall 不会跑
# 2. Playwright 自带的下载器常卡在 0% 不动, 还会把下了一半的包当 "unused" 删掉
# 所以这里手动补跑 postinstall, 浏览器用 curl (可续传) 预下载并写好
# INSTALLATION_COMPLETE 标记, 之后 `dev-browser install` 就不会再下浏览器
set -euo pipefail

prefix=$(npm prefix -g)
pkg="$prefix/lib/node_modules/dev-browser"

[ -d "$pkg" ] || npm install -g dev-browser
compgen -G "$pkg/bin/dev-browser-linux-*" >/dev/null || node "$pkg/scripts/postinstall.js"

# 全局包里的 playwright 与 dev-browser install 装的运行时版本一致, 用它查
# 下载地址与安装位置
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
node "$pkg/node_modules/playwright/cli.js" install --dry-run chromium |
	awk '/Install location:/ {dir = $3} /Download url:/ {print dir, $3}' |
	sort -u |
	while read -r dir url; do
		[ -e "$dir/INSTALLATION_COMPLETE" ] && continue
		echo "下载 $url"
		curl -fsSL --retry 5 --retry-all-errors -C - -o "$tmp/pkg.zip" "$url"
		rm -rf "$dir"
		mkdir -p "$dir"
		unzip -q "$tmp/pkg.zip" -d "$dir"
		rm "$tmp/pkg.zip"
		touch "$dir/INSTALLATION_COMPLETE"
	done

"$prefix/bin/dev-browser" install
