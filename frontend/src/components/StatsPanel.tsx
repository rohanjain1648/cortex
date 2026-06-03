import { KBStats } from '../App'

export default function StatsPanel({ stats }: { stats: KBStats | null }) {
  if (!stats || stats.total_chunks === 0) {
    return <span className="text-xs text-gray-600">No data ingested</span>
  }

  const sources = Object.entries(stats.sources)
    .map(([s, n]) => `${s} ${n}`)
    .join(' · ')

  return (
    <div className="text-right">
      <div className="text-sm font-medium">{stats.total_chunks.toLocaleString()} chunks</div>
      <div className="text-xs text-gray-500">{sources}</div>
    </div>
  )
}
