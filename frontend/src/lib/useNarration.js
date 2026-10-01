import { useSyncExternalStore } from 'react'
import { Narrator } from './narration'
import { mediaUrl } from './media'

// One narrator for the whole app, so playback survives moving between pages (it is an audiobook,
// not a widget of one screen). The bar and the buttons just subscribe to it.
export const narrator = new Narrator({ resolveUrl: mediaUrl })

export function useNarration() {
  const state = useSyncExternalStore(narrator.subscribe, narrator.getSnapshot, narrator.getSnapshot)
  return { narrator, state }
}
