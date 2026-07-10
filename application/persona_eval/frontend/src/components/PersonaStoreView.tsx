import { PersonaStoreContent } from "./PersonaStoreContent";
import { StudioMeshShell, StudioPageFrame, StudioPageHeader } from "./studio/StudioShell";

import type { PersonaPoolPersonaCard } from "@/lib/types";

export interface PersonaStoreViewProps {
  selectedId?: string | null;
  onSelect?: (persona: PersonaPoolPersonaCard) => void;
}

export function PersonaStoreView({ selectedId, onSelect }: PersonaStoreViewProps) {
  return (
    <StudioMeshShell>
      <StudioPageFrame>
        <StudioPageHeader eyebrow="MatrAIx · Persona World" title="Browse personas" />
        <PersonaStoreContent selectedId={selectedId} onSelect={onSelect} autoFocusSearch />
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

export default PersonaStoreView;
