"use client";

type Props = {
  admins: string[];
  activeId: string;
  onSelect: (id: string) => void;
  onAdd: (id: string) => void;
};

const MAX = 10;

export function AdminRoster({ admins, activeId, onSelect, onAdd }: Props) {
  return (
    <section className="panel compact">
      <div className="panel-head">
        <h2>Admins</h2>
        <p>
          {admins.length}/{MAX} slots · used for HITL identity
        </p>
      </div>

      <div className="admin-row">
        {admins.map((id) => (
          <button
            key={id}
            type="button"
            className={`admin-chip ${activeId === id ? "on" : ""}`}
            onClick={() => onSelect(id)}
          >
            {id}
          </button>
        ))}
      </div>

      <button
        type="button"
        className="btn-ghost"
        disabled={admins.length >= MAX}
        onClick={() => {
          const next = `admin-${admins.length + 1}`;
          onAdd(next);
          onSelect(next);
        }}
      >
        {admins.length >= MAX ? "Roster full" : "Add admin"}
      </button>
    </section>
  );
}
