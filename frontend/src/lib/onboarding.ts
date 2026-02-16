/** LocalStorage key for onboarding completion */
export const ONBOARDING_KEY = 'knowledge_onboarding_done'

/** LocalStorage key for note-taking app choice (obsidian when selected, else not set) */
export const NOTE_TAKING_APP_KEY = 'knowledge_note_taking_app'

/** Supported: user can select (toggle). comingSoon: shown but greyed out. */
export interface NoteTakingAppOption {
  id: string
  label: string
  supported: boolean
  comingSoon?: boolean
  logoUrl?: string
}

/** Extensible list. Only Obsidian is supported; others shown as "Coming soon". */
export const NOTE_TAKING_APP_OPTIONS: NoteTakingAppOption[] = [
  {
    id: 'obsidian',
    label: 'Obsidian',
    supported: true,
    logoUrl: 'https://obsidian.md/favicon.ico',
  },
  {
    id: 'notion',
    label: 'Notion',
    supported: false,
    comingSoon: true,
    logoUrl: 'https://www.notion.so/images/favicon.ico',
  },
  {
    id: 'apple-notes',
    label: 'Apple Notes',
    supported: false,
    comingSoon: true,
    logoUrl: '/icons/apple-notes.svg',
  },
  {
    id: 'evernote',
    label: 'Evernote',
    supported: false,
    comingSoon: true,
    logoUrl: 'https://www.evernote.com/favicon.ico',
  },
]
