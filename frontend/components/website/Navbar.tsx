"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { SettingsDropdown } from "./SettingsDropdown";
import { useAuth } from "@/context/AuthContext";

const links = [
  { label: "Features", href: "#features" },
  { label: "Demos", href: "#demos" },
  { label: "Blog", href: "#blog" },
  { label: "Docs", href: "#docs" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, loading } = useAuth();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "glass-nav" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center">
        <Link href="/" className="flex items-center gap-2 flex-shrink-0">
          <span className="text-lg font-bold gradient-text">&lt;/&gt;</span>
          <span className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
            CodeBase<span className="text-[#3b82f6]">AI</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center justify-center gap-8 flex-1">
          {links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm transition-colors hover:opacity-80"
              style={{ color: "var(--text-secondary)" }}
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-medium transition-colors hover:opacity-80 px-4 py-2"
            style={{ color: "var(--text-secondary)" }}
          >
            {user ? "Dashboard" : "Log In"}
          </Link>
          <Link
            href="/agent"
            className="inline-flex items-center px-5 py-2 text-sm font-semibold text-white rounded-xl transition-all duration-300 hover:shadow-[0_0_24px_rgba(59,130,246,0.3)]"
            style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
          >
            {user ? "Open Assistant" : "Try Assistant"}
            <svg className="ml-1.5 w-3.5 h-3.5" viewBox="0 0 16 16" fill="none">
              <path d="M6 3L11 8L6 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </Link>
          {user && (
            <Link
              href="/agent/profile"
              className="flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium"
              style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
              title={user.email || "Profile"}
            >
              {(user.email || "U").charAt(0).toUpperCase()}
            </Link>
          )}
          <SettingsDropdown />
        </div>

        <div className="flex items-center gap-2 md:hidden ml-auto">
          <SettingsDropdown />
          <button
            className="p-1"
            style={{ color: "var(--text-primary)" }}
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            ) : (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div
          className="md:hidden border-t px-6 py-4 space-y-4"
          style={{ background: "var(--bg-secondary)", borderColor: "var(--border-subtle)" }}
        >
          {links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="block text-sm transition-colors hover:opacity-80"
              style={{ color: "var(--text-secondary)" }}
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <Link
            href="/login"
            className="block text-center text-sm font-medium py-2.5 rounded-xl transition-colors"
            style={{ color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
            onClick={() => setMobileOpen(false)}
          >
            {user ? "Dashboard" : "Log In"}
          </Link>
          <Link
            href="/agent"
            className="block text-center text-sm font-semibold text-white py-2.5 rounded-xl"
            style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
            onClick={() => setMobileOpen(false)}
          >
            {user ? "Open Assistant" : "Try Assistant"}
          </Link>
          {user && (
            <Link
              href="/agent/profile"
              className="block text-center text-sm font-medium py-2.5 rounded-xl transition-colors"
              style={{ color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
              onClick={() => setMobileOpen(false)}
            >
              Profile
            </Link>
          )}
        </div>
      )}
    </nav>
  );
}
