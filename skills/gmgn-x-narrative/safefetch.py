# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""外链取标题时的 SSRF 防护 —— 从 MemeX Agent 的 netguard.py 原样带过来。

为什么这个包需要它：web2.py 会去抓推文外链的标题，而**这些 URL 来自推文，
是完全不可信的输入**。没有这层校验，一条推文里放个
`http://169.254.169.254/latest/meta-data/` 就能让脚本去读云厂商的元数据服务，
或者 `http://127.0.0.1:8080/` 去探本机内网服务。

两条关键设计：
  · 解析 DNS 后再判断。光看域名不够 —— attacker.com 的 A 记录完全可以指向
    127.0.0.1，所有解析结果里只要有一个是内网地址就整体拒绝。
  · 每一跳跳转都重新校验。只校验首个 URL 会被 302 到内网绕过。
"""
import ipaddress
import socket
import urllib.parse
import urllib.request


class UnsafeTarget(Exception):
    pass


_BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "ip6-localhost",
                  "metadata", "metadata.google.internal"}


def _ip_is_private(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (addr.is_private or addr.is_loopback or addr.is_link_local
            or addr.is_reserved or addr.is_multicast or addr.is_unspecified)


def check_outbound(url, allow_hosts=None):
    """外链取标题前的校验。返回规范化后的 URL，不安全就抛 UnsafeTarget。

    注意这里解析了 DNS：光看域名不够，attacker.com 完全可以 A 记录指向
    127.0.0.1。所有解析结果里只要有一个是内网地址就整体拒绝。
    """
    if not url or len(url) > 2048:
        raise UnsafeTarget("URL 为空或过长")
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https"):
        raise UnsafeTarget("只允许 http/https：%r" % p.scheme)
    host = (p.hostname or "").lower()
    if not host:
        raise UnsafeTarget("缺少主机名")
    if allow_hosts and host not in allow_hosts:
        raise UnsafeTarget("主机不在允许列表：%s" % host)
    if host in _BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        raise UnsafeTarget("内网主机名：%s" % host)
    if _ip_is_private(host):
        raise UnsafeTarget("内网地址：%s" % host)
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise UnsafeTarget("域名解析失败：%s" % host)
    for info in infos:
        ip = info[4][0]
        if _ip_is_private(ip):
            raise UnsafeTarget("解析到内网地址：%s → %s" % (host, ip))
    return url


def make_safe_opener(max_redirects=3):
    """每一跳跳转都重新校验 —— 只校验首个 URL 会被 302 到内网绕过。"""
    import urllib.request

    class _Handler(urllib.request.HTTPRedirectHandler):
        max_repeats = max_redirects
        max_redirections = max_redirects

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            check_outbound(newurl)
            return urllib.request.HTTPRedirectHandler.redirect_request(
                self, req, fp, code, msg, headers, newurl)

    return urllib.request.build_opener(_Handler)
