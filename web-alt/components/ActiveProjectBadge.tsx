"use client";

import React from "react";
import { useProjectStore } from "../lib/client/useProjectStore";

export default function ActiveProjectBadge() {
  const { activeProject, loading } = useProjectStore();

  return (
    <span className="ml-2 inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
      Project: {loading ? "…" : activeProject ? activeProject.name : "(none)"}
    </span>
  );
}
