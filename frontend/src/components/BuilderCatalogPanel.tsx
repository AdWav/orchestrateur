import {
  IonButton,
  IonInput,
  IonItem,
  IonLabel,
  IonNote,
  IonSelect,
  IonSelectOption,
  IonSpinner,
  IonTextarea,
} from "@ionic/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
  type BuilderBrickSummary,
  type BuilderCompositionItem,
  type BuilderPromotion,
  approveBuilderPromotion,
  createCustomAgentDraft,
  fetchBuilderBricks,
  fetchBuilderCatalogAgents,
  fetchBuilderPromotions,
  fetchCustomAgents,
  publishCustomAgentVersion,
  rejectBuilderPromotion,
  submitBuilderPromotion,
} from "../lib/builderApi";

import "./BuilderCatalogPanel.css";

const SLOT_TYPES = ["role", "capability", "input", "output", "guardrail"] as const;

type SlotId = (typeof SLOT_TYPES)[number];

function buildComposition(
  selected: Partial<Record<SlotId, number[]>>,
): BuilderCompositionItem[] {
  const items: BuilderCompositionItem[] = [];
  for (const slot of SLOT_TYPES) {
    const ids = selected[slot] ?? [];
    ids.forEach((brickId, index) => {
      items.push({ slot, brick_id: brickId, sort_order: index });
    });
  }
  return items;
}

const BuilderCatalogPanel = () => {
  const { t, messages } = useI18n();
  const queryClient = useQueryClient();
  const [activeStep, setActiveStep] = useState(1);
  const [brickTypeFilter, setBrickTypeFilter] = useState<string>("role");
  const [selected, setSelected] = useState<Partial<Record<SlotId, number[]>>>({
    role: [],
    capability: [],
  });
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [mission, setMission] = useState("");
  const [ownerUserId, setOwnerUserId] = useState("user:local");
  const [catalogAgentId, setCatalogAgentId] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [promotionFilter, setPromotionFilter] = useState("submitted");
  const [lastApproveResult, setLastApproveResult] = useState<BuilderPromotion | null>(
    null,
  );
  const [lastPublish, setLastPublish] = useState<{
    runtimeAgentId: string;
    customAgentId: string;
    versionId: number;
  } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const bricksQuery = useQuery({
    queryKey: ["builder-bricks-all"],
    queryFn: () => fetchBuilderBricks(),
    staleTime: 60_000,
  });

  const paletteBricks = useMemo(
    () =>
      (bricksQuery.data ?? []).filter((brick) => brick.type_code === brickTypeFilter),
    [bricksQuery.data, brickTypeFilter],
  );

  const catalogAgentsQuery = useQuery({
    queryKey: ["builder-catalog-agents"],
    queryFn: fetchBuilderCatalogAgents,
    staleTime: 30_000,
  });

  const customAgentsQuery = useQuery({
    queryKey: ["builder-custom-agents", ownerUserId],
    queryFn: () => fetchCustomAgents(ownerUserId),
    staleTime: 10_000,
  });

  const draftMutation = useMutation({
    mutationFn: createCustomAgentDraft,
    onSuccess: () => {
      setActionError(null);
      setActiveStep(3);
      void queryClient.invalidateQueries({ queryKey: ["builder-custom-agents"] });
    },
    onError: (error: Error) => setActionError(error.message),
  });

  const publishMutation = useMutation({
    mutationFn: publishCustomAgentVersion,
    onSuccess: (data) => {
      setActionError(null);
      if (data.runtime_agent_id && data.custom_agent_id) {
        setLastPublish({
          runtimeAgentId: data.runtime_agent_id,
          customAgentId: data.custom_agent_id,
          versionId: data.version_id,
        });
        setActiveStep(4);
      }
      void queryClient.invalidateQueries({ queryKey: ["builder-custom-agents"] });
    },
    onError: (error: Error) => setActionError(error.message),
  });

  const promoteMutation = useMutation({
    mutationFn: submitBuilderPromotion,
    onSuccess: () => {
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ["builder-promotions"] });
    },
    onError: (error: Error) => setActionError(error.message),
  });

  const promotionsQuery = useQuery({
    queryKey: ["builder-promotions", promotionFilter],
    queryFn: () => fetchBuilderPromotions(promotionFilter || undefined),
    staleTime: 5_000,
    enabled: activeStep >= 4,
  });

  const approvePromotionMutation = useMutation({
    mutationFn: ({ id, notes }: { id: number; notes: string }) =>
      approveBuilderPromotion(id, notes ? { review_notes: notes } : {}),
    onSuccess: (data) => {
      setActionError(null);
      setLastApproveResult(data);
      void queryClient.invalidateQueries({ queryKey: ["builder-promotions"] });
      void queryClient.invalidateQueries({ queryKey: ["builder-catalog-agents"] });
    },
    onError: (error: Error) => setActionError(error.message),
  });

  const rejectPromotionMutation = useMutation({
    mutationFn: ({ id, notes }: { id: number; notes: string }) =>
      rejectBuilderPromotion(id, notes ? { review_notes: notes } : {}),
    onSuccess: () => {
      setActionError(null);
      setLastApproveResult(null);
      void queryClient.invalidateQueries({ queryKey: ["builder-promotions"] });
    },
    onError: (error: Error) => setActionError(error.message),
  });

  const catalogCount = catalogAgentsQuery.data?.length ?? 0;
  const customAgents = customAgentsQuery.data ?? [];
  const draftAgents = customAgents.filter((row) => row.status === "draft" && row.version_id);

  const selectedLabels = useMemo(() => {
    const all = bricksQuery.data ?? [];
    const byId = new Map(all.map((brick: BuilderBrickSummary) => [brick.id, brick.label]));
    const labels: string[] = [];
    for (const slot of SLOT_TYPES) {
      for (const id of selected[slot] ?? []) {
        labels.push(`${slot}: ${byId.get(id) ?? id}`);
      }
    }
    return labels;
  }, [selected, bricksQuery.data]);

  const handleCreateDraft = () => {
    setActionError(null);
    const composition = buildComposition(selected);
    if (!(selected.role?.length ?? 0)) {
      setActionError(t("builder.errors.roleRequired"));
      return;
    }
    if (!slug.trim() || !name.trim() || !mission.trim()) {
      setActionError(t("builder.errors.formRequired"));
      return;
    }
    draftMutation.mutate({
      slug: slug.trim(),
      name: name.trim(),
      mission: mission.trim(),
      owner_user_id: ownerUserId.trim(),
      composition,
    });
  };

  const pendingPromotions = (promotionsQuery.data ?? []).filter(
    (row) => row.status === "submitted" || row.status === "in_review",
  );

  const steps = [
    { id: 1, label: messages.builder.steps.palette },
    { id: 2, label: messages.builder.steps.compose },
    { id: 3, label: messages.builder.steps.publish },
    { id: 4, label: messages.builder.steps.promote },
    { id: 5, label: messages.builder.steps.review },
  ];

  return (
    <section className="builder-catalog" aria-labelledby="builder-catalog-title">
      <h2 id="builder-catalog-title" className="builder-catalog__title">
        {messages.builder.panelTitle}
      </h2>
      <p className="builder-catalog__intro">{messages.builder.intro}</p>

      <div className="builder-catalog__steps" role="list">
        {steps.map((step) => (
          <button
            key={step.id}
            type="button"
            role="listitem"
            className={
              activeStep === step.id
                ? "builder-catalog__step-badge builder-catalog__step-badge--active"
                : "builder-catalog__step-badge"
            }
            onClick={() => setActiveStep(step.id)}
          >
            {step.id}. {step.label}
          </button>
        ))}
      </div>

      <IonNote>
        {t("builder.catalogAgentsCount", { count: catalogCount })}
      </IonNote>

      {activeStep === 1 ? (
        <div className="builder-catalog__card" style={{ marginTop: 12 }}>
          <h3>{messages.builder.paletteTitle}</h3>
          <IonItem lines="none">
            <IonLabel position="stacked">{messages.builder.filterType}</IonLabel>
            <IonSelect
              value={brickTypeFilter}
              onIonChange={(event) => setBrickTypeFilter(String(event.detail.value))}
            >
              {SLOT_TYPES.map((slot) => (
                <IonSelectOption key={slot} value={slot}>
                  {slot}
                </IonSelectOption>
              ))}
            </IonSelect>
          </IonItem>
          {bricksQuery.isLoading ? (
            <IonSpinner name="crescent" />
          ) : bricksQuery.isError ? (
            <p className="builder-catalog__error">{messages.builder.apiUnavailable}</p>
          ) : (
            <ul className="builder-catalog__brick-list">
              {paletteBricks.slice(0, 80).map((brick) => (
                <li key={brick.id}>
                  <span>
                    {brick.label}
                    <IonNote> #{brick.id}</IonNote>
                  </span>
                  <span>{brick.domain_code ?? "—"}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="builder-catalog__actions">
            <IonButton onClick={() => setActiveStep(2)}>
              {messages.builder.goToCompose}
            </IonButton>
          </div>
        </div>
      ) : null}

      {activeStep === 2 ? (
        <div className="builder-catalog__grid">
          <div className="builder-catalog__card">
            <h3>{messages.builder.composeTitle}</h3>
            <IonItem>
              <IonLabel position="stacked">{messages.builder.fieldSlug}</IonLabel>
              <IonInput value={slug} onIonInput={(e) => setSlug(e.detail.value ?? "")} />
            </IonItem>
            <IonItem>
              <IonLabel position="stacked">{messages.builder.fieldName}</IonLabel>
              <IonInput value={name} onIonInput={(e) => setName(e.detail.value ?? "")} />
            </IonItem>
            <IonItem>
              <IonLabel position="stacked">{messages.builder.fieldMission}</IonLabel>
              <IonTextarea
                value={mission}
                rows={3}
                onIonInput={(e) => setMission(e.detail.value ?? "")}
              />
            </IonItem>
            <IonItem>
              <IonLabel position="stacked">{messages.builder.fieldOwner}</IonLabel>
              <IonInput
                value={ownerUserId}
                onIonInput={(e) => setOwnerUserId(e.detail.value ?? "")}
              />
            </IonItem>
          </div>

          <div className="builder-catalog__card">
            <h3>{messages.builder.pickBricks}</h3>
            {SLOT_TYPES.map((slot) => (
              <IonItem key={slot} lines="none">
                <IonLabel position="stacked">{slot}</IonLabel>
                <IonSelect
                  multiple={slot !== "role"}
                  value={selected[slot] ?? []}
                  placeholder={messages.builder.selectBricks}
                  onIonChange={(event) => {
                    const value = event.detail.value;
                    const ids = Array.isArray(value)
                      ? value.map((v) => Number(v))
                      : value
                        ? [Number(value)]
                        : [];
                    setSelected((prev) => ({ ...prev, [slot]: ids }));
                  }}
                >
                  {(bricksQuery.data ?? [])
                    .filter((b) => b.type_code === slot)
                    .slice(0, 40)
                    .map((brick) => (
                      <IonSelectOption key={brick.id} value={brick.id}>
                        {brick.label}
                      </IonSelectOption>
                    ))}
                </IonSelect>
              </IonItem>
            ))}
            {selectedLabels.length > 0 ? (
              <div className="builder-catalog__selection">
                {selectedLabels.map((label) => (
                  <span key={label} className="builder-catalog__chip">
                    {label}
                  </span>
                ))}
              </div>
            ) : null}
            <div className="builder-catalog__actions">
              <IonButton
                onClick={() => void handleCreateDraft()}
                disabled={draftMutation.isPending}
              >
                {draftMutation.isPending ? (
                  <IonSpinner name="crescent" />
                ) : (
                  messages.builder.createDraft
                )}
              </IonButton>
            </div>
          </div>
        </div>
      ) : null}

      {activeStep === 3 ? (
        <div className="builder-catalog__card" style={{ marginTop: 12 }}>
          <h3>{messages.builder.publishTitle}</h3>
          {customAgentsQuery.isLoading ? <IonSpinner name="crescent" /> : null}
          {draftAgents.length === 0 ? (
            <IonNote>{messages.builder.noDrafts}</IonNote>
          ) : (
            <ul className="builder-catalog__brick-list">
              {draftAgents.map((agent) => (
                <li key={agent.id}>
                  <span>
                    {agent.slug} (v{agent.version})
                  </span>
                  <IonButton
                    size="small"
                    disabled={publishMutation.isPending}
                    onClick={() => {
                      if (agent.version_id) {
                        publishMutation.mutate(agent.version_id);
                      }
                    }}
                  >
                    {messages.builder.publish}
                  </IonButton>
                </li>
              ))}
            </ul>
          )}
          {lastPublish ? (
            <div className="builder-catalog__result">
              <strong>{messages.builder.publishDone}</strong>
              <br />
              runtime: <code>{lastPublish.runtimeAgentId}</code>
              <br />
              custom_id: <code>{lastPublish.customAgentId}</code>
            </div>
          ) : null}
          <div className="builder-catalog__actions">
            <IonButton onClick={() => setActiveStep(4)} disabled={!lastPublish}>
              {messages.builder.goToPromote}
            </IonButton>
          </div>
        </div>
      ) : null}

      {activeStep === 4 ? (
        <div className="builder-catalog__card" style={{ marginTop: 12 }}>
          <h3>{messages.builder.promoteTitle}</h3>
          <IonNote>{messages.builder.promoteHint}</IonNote>
          <IonItem>
            <IonLabel position="stacked">{messages.builder.fieldCatalogId}</IonLabel>
            <IonInput
              value={catalogAgentId}
              onIonInput={(e) => setCatalogAgentId(e.detail.value ?? "")}
              placeholder="my_official_agent"
            />
          </IonItem>
          <div className="builder-catalog__actions">
            <IonButton
              disabled={!lastPublish || !catalogAgentId.trim() || promoteMutation.isPending}
              onClick={() => {
                if (!lastPublish) {
                  return;
                }
                promoteMutation.mutate({
                  requester_id: ownerUserId.trim(),
                  source_kind: "custom_agent",
                  source_id: lastPublish.customAgentId,
                  target_kind: "builder_agent",
                  target_id: catalogAgentId.trim(),
                  proposed_payload: { domain_code: "dev" },
                });
              }}
            >
              {messages.builder.submitPromotion}
            </IonButton>
          </div>
          {promoteMutation.isSuccess ? (
            <div className="builder-catalog__result">{messages.builder.promoteSubmitted}</div>
          ) : null}
          <div className="builder-catalog__actions">
            <IonButton onClick={() => setActiveStep(5)}>
              {messages.builder.goToReview}
            </IonButton>
          </div>
        </div>
      ) : null}

      {activeStep === 5 ? (
        <div className="builder-catalog__card" style={{ marginTop: 12 }}>
          <h3>{messages.builder.reviewTitle}</h3>
          <IonNote>{messages.builder.reviewHint}</IonNote>
          <IonItem lines="none">
            <IonLabel position="stacked">{messages.builder.reviewNotes}</IonLabel>
            <IonTextarea
              value={reviewNotes}
              rows={2}
              onIonInput={(e) => setReviewNotes(e.detail.value ?? "")}
            />
          </IonItem>
          <IonItem lines="none">
            <IonLabel position="stacked">{messages.builder.promotionFilter}</IonLabel>
            <IonSelect
              value={promotionFilter}
              onIonChange={(e) => setPromotionFilter(String(e.detail.value))}
            >
              <IonSelectOption value="submitted">{messages.builder.filterSubmitted}</IonSelectOption>
              <IonSelectOption value="approved">{messages.builder.filterApproved}</IonSelectOption>
              <IonSelectOption value="rejected">{messages.builder.filterRejected}</IonSelectOption>
              <IonSelectOption value="">{messages.builder.filterAll}</IonSelectOption>
            </IonSelect>
          </IonItem>
          {promotionsQuery.isLoading ? <IonSpinner name="crescent" /> : null}
          {promotionsQuery.isError ? (
            <p className="builder-catalog__error">{messages.builder.apiUnavailable}</p>
          ) : null}
          {!promotionsQuery.isLoading && (promotionsQuery.data ?? []).length === 0 ? (
            <IonNote>{messages.builder.noPromotions}</IonNote>
          ) : (
            <div style={{ marginTop: 8 }}>
              {(promotionsQuery.data ?? []).map((promo) => (
                <div key={promo.id} className="builder-catalog__promo-row">
                  <strong>
                    #{promo.id} — {promo.status}
                  </strong>
                  <div className="builder-catalog__promo-meta">
                    {promo.source_kind} / {promo.source_id.slice(0, 8)}… → {promo.target_kind}
                    {promo.target_id ? ` / ${promo.target_id}` : ""}
                    <br />
                    {messages.builder.requester}: {promo.requester_id}
                  </div>
                  {promo.status === "approved" && promo.catalog_agent_id ? (
                    <div className="builder-catalog__result">
                      {t("builder.approvedCatalogAgent", {
                        agentId: promo.catalog_agent_id,
                        versionId: promo.catalog_version_id ?? "—",
                      })}
                    </div>
                  ) : null}
                  {promo.status === "submitted" || promo.status === "in_review" ? (
                    <div className="builder-catalog__promo-actions">
                      <IonButton
                        color="success"
                        size="small"
                        disabled={
                          approvePromotionMutation.isPending ||
                          rejectPromotionMutation.isPending
                        }
                        onClick={() =>
                          approvePromotionMutation.mutate({
                            id: promo.id,
                            notes: reviewNotes.trim(),
                          })
                        }
                      >
                        {messages.builder.approvePromotion}
                      </IonButton>
                      <IonButton
                        color="medium"
                        size="small"
                        fill="outline"
                        disabled={
                          approvePromotionMutation.isPending ||
                          rejectPromotionMutation.isPending
                        }
                        onClick={() =>
                          rejectPromotionMutation.mutate({
                            id: promo.id,
                            notes: reviewNotes.trim(),
                          })
                        }
                      >
                        {messages.builder.rejectPromotion}
                      </IonButton>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
          {lastApproveResult?.catalog_agent_id ? (
            <div className="builder-catalog__result">
              {t("builder.approvedCatalogAgent", {
                agentId: lastApproveResult.catalog_agent_id,
                versionId: lastApproveResult.catalog_version_id ?? "—",
              })}
            </div>
          ) : null}
          {pendingPromotions.length > 0 && activeStep === 5 ? (
            <IonNote>
              {t("builder.pendingCount", { count: pendingPromotions.length })}
            </IonNote>
          ) : null}
        </div>
      ) : null}

      {actionError ? <p className="builder-catalog__error">{actionError}</p> : null}
    </section>
  );
};

export default BuilderCatalogPanel;
