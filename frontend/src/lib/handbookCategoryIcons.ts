const SVG_ATTRS = `viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14" aria-hidden="true"`;

const icons: Record<string, string> = {
  // CS Fundamentals — terminal/code
  'cs-fundamentals': `<svg ${SVG_ATTRS}><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`,

  // Math & Statistics — sigma/function
  'math-statistics': `<svg ${SVG_ATTRS}><path d="M18 7V4H6l6 8-6 8h12v-3"/></svg>`,

  // ML Fundamentals — scatter/chart
  'ml-fundamentals': `<svg ${SVG_ATTRS}><circle cx="7.5" cy="7.5" r="1.5"/><circle cx="18" cy="18" r="1.5"/><circle cx="11" cy="15" r="1.5"/><circle cx="16.5" cy="9.5" r="1.5"/><circle cx="7" cy="13" r="1.5"/><path d="M3 3v18h18"/></svg>`,

  // Deep Learning — layers/neural network
  'deep-learning': `<svg ${SVG_ATTRS}><path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>`,

  // LLM & Generative AI — sparkles/brain
  'llm-genai': `<svg ${SVG_ATTRS}><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/></svg>`,

  // Data Engineering — database/pipeline
  'data-engineering': `<svg ${SVG_ATTRS}><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,

  // Infra & Hardware — cpu/gpu chip
  'infra-hardware': `<svg ${SVG_ATTRS}><rect x="4" y="4" width="16" height="16" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>`,

  // AI Safety & Ethics — shield with check
  'safety-ethics': `<svg ${SVG_ATTRS}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>`,

  // Products & Platforms — package/box
  'products-platforms': `<svg ${SVG_ATTRS}><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>`,
};

const fallback = `<svg ${SVG_ATTRS}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

export function getHandbookCategoryIcon(id: string): string {
  return icons[id] ?? fallback;
}
