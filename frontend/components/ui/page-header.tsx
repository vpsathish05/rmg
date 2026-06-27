interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export function PageHeader({ title, subtitle, action }: PageHeaderProps) {
  return (
    <div
      className="flex items-center justify-between px-8 py-5 bg-card border-b border-border shrink-0"
      style={{ borderLeft: "4px solid #3411A3" }}
    >
      <div>
        <h1 className="text-lg font-bold" style={{ color: "#19105B" }}>{title}</h1>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
