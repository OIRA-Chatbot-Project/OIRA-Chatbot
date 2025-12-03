"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { v4 as uuidv4 } from "uuid";
import ChatInterface from "./components/ChatInterface";
import Sidebar from "./components/Sidebar";
import { SessionSummary, Theme } from "./types";
import { DEFAULT_SESSION_TITLE } from "./utils/session";
import {
  saveCurrentSessionId,
  loadCurrentSessionId,
  clearLegacyStorage,
} from "./utils/sessionStorage";
import { initializeUserInBackend } from "./utils/api";
import { useSessionManager } from "./utils/useSessionManager";

export default function Home() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const [theme, setTheme] = useState<Theme>("light");
  const [isCurrentSessionEmpty, setIsCurrentSessionEmpty] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  const {
    sessions,
    sessionId,
    isCreatingSession,
    isTemporarySession,
    setSessionId,
    setIsCreatingSession,
    setIsTemporarySession,
    persistSessions,
    updateSessionTitle,
    switchSession,
    markSessionHasMessages,
    hydrateSessionTitles,
    loadUserSessions,
  } = useSessionManager(user?.id, getToken, isLoaded, isSignedIn || false);

  // Theme initialization and persistence
  useEffect(() => {
    if (typeof window === "undefined") return;

    const savedTheme = localStorage.getItem("theme") as Theme | null;
    if (savedTheme) {
      setTheme(savedTheme);
      return;
    }

    if (window.matchMedia?.("(prefers-color-scheme: dark)").matches) {
      setTheme("dark");
    }
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;

    document.documentElement.dataset.theme = theme;
    document.body.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }, []);

  // Update current session empty state
  useEffect(() => {
    // Temporary sessions are always empty initially
    if (isTemporarySession) {
      setIsCurrentSessionEmpty(true);
      return;
    }

    const current = sessions.find((session) => session.id === sessionId);
    setIsCurrentSessionEmpty(current ? !current.hasMessages : false);
  }, [sessionId, sessions, isTemporarySession]);

  const startNewChat = useCallback(() => {
    if (isCreatingSession) return;

    setIsCreatingSession(true);
    const newSessionId = uuidv4();

    // Don't add to sessions list - make it temporary
    setSessionId(newSessionId);
    setIsTemporarySession(true);

    if (user?.id) {
      saveCurrentSessionId(user.id, newSessionId);
    }

    setIsCreatingSession(false);
  }, [
    isCreatingSession,
    setSessionId,
    setIsTemporarySession,
    user,
    setIsCreatingSession,
  ]);

  const deleteSession = useCallback(
    (id: string) => {
      persistSessions((prev) => prev.filter((session) => session.id !== id));

      if (id === sessionId) {
        startNewChat();
      }
    },
    [persistSessions, sessionId, startNewChat]
  );

  // Load user sessions from backend - only after user is initialized
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !user || !isInitialized) return;

    let isMounted = true;

    const initializeSessions = async () => {
      try {
        // Load existing sessions from backend
        const result = await loadUserSessions();

        if (result.shouldContinue && result.sessions && isMounted) {
          // Hydrate titles in background without blocking
          hydrateSessionTitles(result.sessions, () => isMounted);
        }
        
        // Check if this is a fresh access or a reload
        // sessionStorage persists during page reloads but not new tabs/windows
        const hasActiveSession = sessionStorage.getItem('hasActiveSession');
        
        if (!hasActiveSession) {
          // First access in this tab - create new temporary chat
          if (isMounted) {
            startNewChat();
            sessionStorage.setItem('hasActiveSession', 'true');
          }
        } else if (result.shouldContinue && result.sessions && result.sessions.length > 0) {
          // Reload - restore the last active session
          const savedSessionId = user?.id ? loadCurrentSessionId(user.id) : null;
          const activeSessionId = 
            savedSessionId && result.sessions.find(s => s.id === savedSessionId)
              ? savedSessionId
              : result.sessions[0].id;
          
          if (isMounted) {
            setSessionId(activeSessionId);
            if (user?.id) {
              saveCurrentSessionId(user.id, activeSessionId);
            }
          }
        } else {
          // Reload but no existing sessions - create temporary
          if (isMounted) {
            startNewChat();
          }
        }
      } catch (error) {
        console.error("Failed to initialize sessions:", error);
        // Create temporary session on error
        if (isMounted) {
          startNewChat();
        }
      }
    };

    initializeSessions();

    return () => {
      isMounted = false;
    };
  }, [
    isLoaded,
    isSignedIn,
    user,
    isInitialized,
    loadUserSessions,
    hydrateSessionTitles,
    startNewChat,
    setSessionId,
  ]);

  // Initialize user in backend
  useEffect(() => {
    if (isInitialized) return; // Prevent multiple initialization attempts

    async function initializeUser() {
      if (!isLoaded || !isSignedIn || !user) return;

      clearLegacyStorage();

      try {
        const token = await getToken();
        if (!token) {
          console.error("Failed to get authentication token");
          return;
        }

        const success = await initializeUserInBackend(
          token,
          user.id,
          user.primaryEmailAddress?.emailAddress || "",
          user.fullName
        );

        if (success) {
          setIsInitialized(true);
        }
      } catch (error) {
        console.error("Failed to initialize user:", error);
        // Still set initialized to prevent infinite retry
        setIsInitialized(true);
      }
    }

    initializeUser();
  }, [isLoaded, isSignedIn, user, getToken, isInitialized]);

  // Loading state
  if (!isLoaded || (isSignedIn && !isInitialized)) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  // Not signed in (middleware will redirect)
  if (!isSignedIn) {
    return null;
  }

  return (
    <div
      className={`flex h-screen overflow-hidden ${
        theme === "dark"
          ? "text-gray-100 bg-transparent"
          : "text-gray-900 bg-transparent"
      }`}
    >
      <Sidebar
        sessions={sessions.filter((s) => !s.isTemporary)}
        currentSessionId={sessionId}
        onNewChat={startNewChat}
        onSelectSession={switchSession}
        onDeleteSession={deleteSession}
        theme={theme}
        disableNewChat={isCreatingSession}
      />
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {sessionId && (
          <ChatInterface
            key={sessionId}
            sessionId={sessionId}
            onSessionTitleUpdate={updateSessionTitle}
            onSessionHasMessages={markSessionHasMessages}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
        )}
      </main>
    </div>
  );
}
