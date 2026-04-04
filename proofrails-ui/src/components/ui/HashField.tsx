type HashFieldProps = {
  value: string;
  label?: string;
  truncate?: boolean;
  className?: string;
};

export function HashField({ value, label, truncate = true, className = '' }: HashFieldProps) {
  const display =
    truncate && value.length > 18 && !value.startsWith('—')
      ? `${value.slice(0, 10)}…${value.slice(-8)}`
      : value;

  return (
    <div className={className}>
      {label ? (
        <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-500">
          {label}
        </p>
      ) : null}
      <code
        className="block font-mono text-[13px] leading-relaxed text-cyan-100/90"
        title={value}
      >
        {display}
      </code>
    </div>
  );
}
