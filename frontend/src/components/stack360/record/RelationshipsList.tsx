import Link from "next/link";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { Badge } from "@/components/ui/Badge";
import type { CompanyPersonLink, PersonCompanyLink } from "@/lib/stack360/types";

export function PersonCompaniesList({ links }: { links: PersonCompanyLink[] }) {
  if (links.length === 0) {
    return (
      <BrutalCard>
        <p className="font-headline text-sm font-black uppercase text-ink/60">Nenhuma empresa relacionada.</p>
      </BrutalCard>
    );
  }

  return (
    <BrutalCard>
      <h3 className="mb-3 border-b-2 border-ink/20 pb-2 font-headline text-sm font-black uppercase tracking-widest text-ink/70">
        Empresas relacionadas
      </h3>
      <div className="flex flex-col divide-y-2 divide-ink/10">
        {links.map(({ company, relationship }) => (
          <div key={company.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <Link href={`/companies/${company.id}`} className="font-headline text-sm font-black uppercase underline">
              {company.canonical_name}
            </Link>
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-ink/60">
              {relationship.role ? <Badge tone="default">{relationship.role}</Badge> : null}
              {relationship.is_current ? <Badge tone="yellow">Atual</Badge> : null}
            </div>
          </div>
        ))}
      </div>
    </BrutalCard>
  );
}

export function CompanyPeopleList({ links }: { links: CompanyPersonLink[] }) {
  if (links.length === 0) {
    return (
      <BrutalCard>
        <p className="font-headline text-sm font-black uppercase text-ink/60">Nenhuma pessoa relacionada.</p>
      </BrutalCard>
    );
  }

  return (
    <BrutalCard>
      <h3 className="mb-3 border-b-2 border-ink/20 pb-2 font-headline text-sm font-black uppercase tracking-widest text-ink/70">
        Pessoas relacionadas
      </h3>
      <div className="flex flex-col divide-y-2 divide-ink/10">
        {links.map(({ person, relationship }) => (
          <div key={person.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <Link href={`/people/${person.id}`} className="font-headline text-sm font-black uppercase underline">
              {person.canonical_name}
            </Link>
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-ink/60">
              {relationship.role ? <Badge tone="default">{relationship.role}</Badge> : null}
              {relationship.is_current ? <Badge tone="yellow">Atual</Badge> : null}
            </div>
          </div>
        ))}
      </div>
    </BrutalCard>
  );
}
