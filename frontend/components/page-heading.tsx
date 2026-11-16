export function PageHeading({
  title,
  children,
  actions,
}: {
  title: string;
  children?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-[28px] font-semibold tracking-tight">{title}</h1>
        {children ? <p className="text-sm text-muted-foreground">{children}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

export function Panel({
  title,
  id,
  aside,
  children,
}: {
  title: string;
  id: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4 rounded-xl border bg-card p-6">
      <div className="flex items-center justify-between gap-4">
        <h2 id={id} className="text-base font-semibold">
          {title}
        </h2>
        {aside ? <div className="text-[13px] text-muted-foreground">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}
