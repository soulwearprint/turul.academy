/**
 * TurulPortrait — the illustrated Turul companion (raster art).
 *
 * Used for hero / showcase contexts where the rich illustration shines.
 * For small, recolorable, or animated icon contexts, use TurulMascot (SVG).
 *
 * Art evolves by stage: explorer → adventurer → scholar → mentor.
 * Pass either `stage` directly or a `grade` (mapped via stageForGrade).
 */
import explorer from '../assets/mascot/explorer.png'
import adventurer from '../assets/mascot/adventurer.png'
import scholar from '../assets/mascot/scholar.png'
import mentor from '../assets/mascot/mentor.png'
import { stageForGrade } from '../lib/turul'

const ART = { explorer, adventurer, scholar, mentor }

export default function TurulPortrait({
  stage,
  grade,
  size = 160,
  animate = true,
  className = '',
  alt = 'Turul',
}) {
  const key = stage ?? (grade != null ? stageForGrade(grade).key : 'adventurer')
  return (
    <img
      src={ART[key] ?? adventurer}
      alt={alt}
      width={size}
      height={size}
      className={`inline-block object-contain ${animate ? 'animate-float' : ''} ${className}`}
      style={{ width: size, height: size }}
    />
  )
}
