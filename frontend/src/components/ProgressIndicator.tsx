export function ProgressIndicator({ step, total }: { step: number; total: number }) {
  return (
    <div className="w-full h-1 bg-slate-200 rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-navy-900 to-gold-500 transition-all duration-500"
        style={{ width: `${Math.min((step / total) * 100, 100)}%` }}
      />
    </div>
  )
}
