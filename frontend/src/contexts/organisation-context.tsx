import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/contexts/auth-context";
import { getOrganisations, type Organisation } from "@/services/dashboard";

interface OrganisationContextType {
  organisations: Organisation[];
  selectedOrganisationId: string;
  setSelectedOrganisationId: (id: string) => void;
  isLoadingOrganisations: boolean;
}

const OrganisationContext = createContext<OrganisationContextType | undefined>(
  undefined,
);

export function OrganisationProvider({ children }: { children: ReactNode }) {
  const { user, isLoading: isAuthLoading } = useAuth();

  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [selectedOrganisationId, setSelectedOrganisationId] = useState("");
  const [isLoadingOrganisations, setIsLoadingOrganisations] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadOrganisations() {
      if (isAuthLoading) {
        return;
      }

      if (!user) {
        setOrganisations([]);
        setSelectedOrganisationId("");
        setIsLoadingOrganisations(false);
        return;
      }

      setIsLoadingOrganisations(true);

      try {
        const data = await getOrganisations();

        if (!active) return;

        setOrganisations(data);

        setSelectedOrganisationId((currentId) => {
          const currentOrganisation = data.find(
            (organisation) => organisation.id === currentId,
          );

          if (currentOrganisation) return currentId;

          const defaultOrganisation = data.find(
            (organisation) => organisation.name === "ResolveIQ Demo Two",
          );

          return defaultOrganisation?.id ?? data[0]?.id ?? "";
        });
      } catch (error) {
        if (active) {
          console.error("Failed to load organisations:", error);
          setOrganisations([]);
          setSelectedOrganisationId("");
        }
      } finally {
        if (active) {
          setIsLoadingOrganisations(false);
        }
      }
    }

    void loadOrganisations();

    return () => {
      active = false;
    };
  }, [user?.id, isAuthLoading]);

  return (
    <OrganisationContext.Provider
      value={{
        organisations,
        selectedOrganisationId,
        setSelectedOrganisationId,
        isLoadingOrganisations,
      }}
    >
      {children}
    </OrganisationContext.Provider>
  );
}

export function useOrganisation() {
  const context = useContext(OrganisationContext);

  if (!context) {
    throw new Error("useOrganisation must be used inside OrganisationProvider");
  }

  return context;
}
