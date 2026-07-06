// AuthContext — Supabase auth state management with profile fetching

"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { User } from "@supabase/supabase-js";
import { getSupabase } from "@/lib/supabase";

// User profile shape from backend
interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  bio?: string;
}

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  backendError: string | null;
  signIn: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<{ error?: string }>;
  signUpWithEmail: (email: string, password: string, name?: string) => Promise<{ error?: string }>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  profile: null,
  loading: true,
  backendError: null,
  signIn: async () => {},
  signInWithEmail: async () => ({}),
  signUpWithEmail: async () => ({}),
  signOut: async () => {},
  refreshProfile: async () => {},
});

// Hook to access auth context
export function useAuth() {
  return useContext(AuthContext);
}

// AuthProvider — manages user session, profile data, and sign in/out
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState<string | null>(null);

  // Fetch user profile from backend
  const fetchProfile = useCallback(async (userId: string) => {
    try {
      const supabase = getSupabase();
      if (!supabase) return;
      const res = await fetch("/api/auth/me", {
        headers: {
          Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Unknown error" }));
        setBackendError(err.error || `Auth service returned ${res.status}`);
        return;
      }
      const data = await res.json();
      if (data.authenticated && data.user) {
        setProfile(data.user);
        setBackendError(null);
      }
    } catch {
      setBackendError("Cannot connect to authentication service. Please try again later.");
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (user) {
      await fetchProfile(user.id);
    }
  }, [user, fetchProfile]);

  // Listen for session changes on mount
  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setLoading(false);
      return;
    }
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user.id);
      }
      setLoading(false);
    });

    // Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user.id);
      } else {
        setProfile(null);
      }
    });

    return () => subscription.unsubscribe();
  }, [fetchProfile]);

  // Sign in with Google OAuth
  const signIn = useCallback(async () => {
    setBackendError(null);
    const supabase = getSupabase();
    if (!supabase) {
      setBackendError("Authentication is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.");
      return;
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/agent`,
      },
    });
    if (error) {
      setBackendError(`OAuth sign-in failed: ${error.message}`);
    }
  }, []);

  // Sign in with email/password
  const signInWithEmail = useCallback(async (email: string, password: string) => {
    setBackendError(null);
    const supabase = getSupabase();
    if (!supabase) return { error: "Authentication is not configured." };
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { error: error.message };
    return {};
  }, []);

  // Sign up with email/password
  const signUpWithEmail = useCallback(async (email: string, password: string, name?: string) => {
    setBackendError(null);
    const supabase = getSupabase();
    if (!supabase) return { error: "Authentication is not configured." };
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: name ? { data: { full_name: name } } : undefined,
    });
    if (error) return { error: error.message };
    return {};
  }, []);

  // Sign out and clear state
  const signOut = useCallback(async () => {
    const supabase = getSupabase();
    if (!supabase) return;
    await supabase.auth.signOut();
    setUser(null);
    setProfile(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, profile, loading, backendError, signIn, signInWithEmail, signUpWithEmail, signOut, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}
