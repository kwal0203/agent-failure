import { getLabGuideContent } from "../labGuideContent";

type LabGuideColumnProps = {
  labId?: string | null;
};

export function LabGuideColumn({ labId }: LabGuideColumnProps) {
  const content = getLabGuideContent(labId);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <section className="lab-guide-scroll-region min-h-0 flex-[1_1_auto] overflow-y-auto rounded-lg border border-slate-300/90 bg-slate-950/20 p-4">
        <h2 className="m-0 text-lg font-semibold tracking-wide text-slate-100">
          Lab Guide
        </h2>
        <p className="mb-1 mt-2 font-semibold text-slate-100">
          {content.title}
        </p>
        <div className="mt-5">
          <h3 className="m-0 text-lg font-semibold tracking-wide text-slate-100">
            Mission Summary
          </h3>
          <p className="mb-2 mt-0 text-slate-100">
            <strong>Objective:</strong> {content.objective}
          </p>
          <p className="mb-2 mt-0 text-slate-100">
            <strong>Target:</strong> {content.target}
          </p>
          <p className="m-0 text-slate-100">
            <strong>Attack Vector:</strong> {content.attackVector}
          </p>
        </div>
        <div className="mt-5">
          <h3 className="mb-2 mt-0 text-base font-semibold text-slate-100">
            Success Criteria
          </h3>
          <ul className="m-0 list-disc pl-5 text-slate-200">
            {content.successCriteria.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="mt-5">
          <h3 className="mb-2 mt-0 text-base font-semibold text-slate-100">
            Evidence to Capture
          </h3>
          <ul className="m-0 list-disc pl-5 text-slate-200">
            {content.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>

      <style>{`
        .lab-guide-scroll-region {
          scrollbar-width: thin;
          scrollbar-color: #88a2b8 transparent;
        }
        .lab-guide-scroll-region::-webkit-scrollbar {
          width: 10px;
        }
        .lab-guide-scroll-region::-webkit-scrollbar-track {
          background: transparent;
        }
        .lab-guide-scroll-region::-webkit-scrollbar-thumb {
          background-color: #88a2b8;
          border-radius: 999px;
          border: 2px solid transparent;
          background-clip: content-box;
        }
        .lab-guide-scroll-region::-webkit-scrollbar-thumb:hover {
          background-color: #6f8ea8;
        }
      `}</style>
    </div>
  );
}
