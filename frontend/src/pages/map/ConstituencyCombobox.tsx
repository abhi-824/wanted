import { useEffect, useId, useMemo, useRef, useState } from 'react'

const MAX_OPTIONS = 60

function highlightMatch(text: string, query: string) {
  if (!query) return text
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <span className="match">{text.slice(idx, idx + query.length)}</span>
      {text.slice(idx + query.length)}
    </>
  )
}

type ConstituencyComboboxProps = {
  names: string[]
  value: string
  onChange: (name: string) => void
}

export default function ConstituencyCombobox({ names, value, onChange }: ConstituencyComboboxProps) {
  const listId = useId()
  const wrapRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [inputValue, setInputValue] = useState(value)
  const [open, setOpen] = useState(false)
  const [focusedIdx, setFocusedIdx] = useState(-1)

  useEffect(() => {
    setInputValue(value)
  }, [value])

  const query = inputValue.trim()
  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    const list = q ? names.filter((n) => n.toLowerCase().includes(q)) : names
    return list.slice(0, MAX_OPTIONS)
  }, [names, query])

  const activeOptionId =
    focusedIdx >= 0 && focusedIdx < filtered.length ? `${listId}-opt-${focusedIdx}` : undefined

  function close() {
    setOpen(false)
    setFocusedIdx(-1)
  }

  function select(name: string) {
    onChange(name)
    setInputValue(name)
    close()
    inputRef.current?.blur()
  }

  function openList() {
    setOpen(true)
    setFocusedIdx(-1)
  }

  useEffect(() => {
    function onDocMouseDown(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) close()
    }
    document.addEventListener('mousedown', onDocMouseDown)
    return () => document.removeEventListener('mousedown', onDocMouseDown)
  }, [])

  return (
    <div className="combo-wrap" ref={wrapRef}>
      <input
        ref={inputRef}
        id={`${listId}-input`}
        className="combo-input"
        type="text"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={activeOptionId}
        placeholder="Type constituency name..."
        autoComplete="off"
        spellCheck={false}
        value={inputValue}
        onFocus={() => openList()}
        onChange={(e) => {
          const next = e.target.value
          setInputValue(next)
          if (value && next !== value) onChange('')
          openList()
        }}
        onKeyDown={(e) => {
          if (!open) {
            openList()
            return
          }
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setFocusedIdx((i) => Math.min(i + 1, filtered.length - 1))
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setFocusedIdx((i) => Math.max(i - 1, -1))
          } else if (e.key === 'Enter') {
            e.preventDefault()
            const pick =
              focusedIdx >= 0 ? filtered[focusedIdx] : filtered.length === 1 ? filtered[0] : undefined
            if (pick) select(pick)
          } else if (e.key === 'Escape') {
            close()
            inputRef.current?.blur()
          }
        }}
      />
      {inputValue ? (
        <button
          type="button"
          className="combo-clear"
          style={{ display: 'block' }}
          title="Clear"
          aria-label="Clear search"
          onMouseDown={(e) => {
            e.preventDefault()
            setInputValue('')
            onChange('')
            openList()
            inputRef.current?.focus()
          }}
        >
          ✕
        </button>
      ) : null}
      {open ? (
        <div
          id={listId}
          className="combo-dropdown"
          role="listbox"
          style={{ display: 'block' }}
          onMouseDown={(e) => {
            const opt = (e.target as Element).closest('[data-name]') as HTMLElement | null
            if (opt?.dataset.name) {
              e.preventDefault()
              select(opt.dataset.name)
            }
          }}
        >
          {filtered.length === 0 ? (
            <div className="combo-empty">NO MATCH FOUND</div>
          ) : (
            filtered.map((name, i) => (
              <div
                key={name}
                id={`${listId}-opt-${i}`}
                role="option"
                aria-selected={name === value}
                className={i === focusedIdx ? 'combo-option focused' : 'combo-option'}
                data-name={name}
              >
                {highlightMatch(name, query)}
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  )
}
