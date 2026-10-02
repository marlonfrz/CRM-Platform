"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { createStore, useStore, type StoreApi } from "zustand";

import type { ActivityPage } from "@/lib/activities";

type ActivityOptions = Pick<ActivityPage, "departments" | "candidates" | "activity_types" | "can_create">;
type ActivityOptionsState = { options: ActivityOptions };

const ActivityOptionsContext = createContext<StoreApi<ActivityOptionsState> | null>(null);

export function ActivityOptionsProvider({ options, children }: { options: ActivityOptions; children: ReactNode }) {
  const [store] = useState(() => createStore<ActivityOptionsState>()(() => ({ options })));

  useEffect(() => {
    store.setState({ options });
  }, [store, options]);

  return <ActivityOptionsContext.Provider value={store}>{children}</ActivityOptionsContext.Provider>;
}

export function useActivityOptions(): ActivityOptions {
  const store = useContext(ActivityOptionsContext);
  if (!store) throw new Error("Activity options must be used within ActivityOptionsProvider");
  return useStore(store, (state) => state.options);
}
