"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { listAdmins, useMocks } from "@/lib/api";
import { CrossUserActions } from "@/components/CrossUserActions";
import { SandboxWorld } from "@/components/SandboxWorld";
import type { AdminListResponse } from "@/lib/types";

type Props = {
  params: Promise<{ adminId: string }>;
};

export default function SandboxAdminPage({ params }: Props) {
  const { adminId } = use(params);
  const decoded = decodeURIComponent(adminId);
  const mocks = useMocks();
  const [roster, setRoster] = useState<AdminListResponse | null>(null);
  const [actionTick, setActionTick] = useState(0);

  useEffect(() => {
    void listAdmins()
      .then(setRoster)
      .catch(() => setRoster(null));
  }, [mocks]);

  return (
    <main className="shell shell-narrow">
      <p className="sandbox-desk-nav">
        <Link href="/sandbox" className="btn-ghost">
          ← All desks
        </Link>
      </p>
      <SandboxWorld
        adminId={decoded}
        variant="page"
        pollMs={2000}
        refreshKey={actionTick}
      />
      <CrossUserActions
        roster={roster}
        fromAdminId={decoded}
        onDone={() => setActionTick((n) => n + 1)}
      />
    </main>
  );
}
