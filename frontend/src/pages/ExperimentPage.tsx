import { useEffect, useState } from 'react';
import {
  AppShell,
  Alert,
  Anchor,
  Container,
  Group,
  Loader,
  Stack,
  Stepper,
  Text,
  Title,
} from '@mantine/core';
import { Link, useParams } from 'react-router-dom';
import { useExperiment } from '../api/experiments';
import type { ExperimentMode, Progress } from '../api/types';
import { CompletedStep } from './steps/CompletedStep';
import { PredictionStep } from './steps/PredictionStep';
import { ReactionScopeStep } from './steps/ReactionScopeStep';
import { TrainingStep } from './steps/TrainingStep';

function activeStep(
  mode: ExperimentMode,
  progress: Progress,
  reactionScopeAcknowledged: boolean,
  trainingAcknowledged: boolean,
): number {
  const reactionScopeDone = progress.reaction_scope && reactionScopeAcknowledged;
  if (!reactionScopeDone) return 0;
  const trainingDone = mode !== 'new' || (progress.training_set && trainingAcknowledged);
  if (mode === 'new' && !trainingDone) return 1;
  if (!progress.optimization) return mode === 'new' ? 2 : 1;
  return mode === 'new' ? 3 : 2;
}

export function ExperimentPage() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const { data: experiment, isPending, isError, error } = useExperiment(experimentId ?? '');

  // These gate a step transition behind an explicit "continue" click rather
  // than sweeping the user straight into the next step the instant the
  // backend flips the corresponding progress flag — but only for a
  // transition that happens *during this visit*. Each starts null and gets
  // locked in exactly once, to whatever the flag already was the first time
  // real data arrives for this experiment: if it was already done then,
  // there's nothing to confirm and the step is skipped outright; only if it
  // flips true *after* that snapshot do we require the click. Without the
  // snapshot, every revisit to an already-advanced experiment (navigating
  // away and back, reloading) would re-show a stale "just completed!"
  // screen for stages finished in a previous visit.
  const [reactionScopeAcknowledged, setReactionScopeAcknowledged] = useState<boolean | null>(
    null,
  );
  const [trainingAcknowledged, setTrainingAcknowledged] = useState<boolean | null>(null);

  useEffect(() => {
    setReactionScopeAcknowledged(null);
    setTrainingAcknowledged(null);
  }, [experimentId]);

  useEffect(() => {
    if (!experiment) return;
    setReactionScopeAcknowledged((prev) => prev ?? experiment.progress.reaction_scope);
    setTrainingAcknowledged((prev) => prev ?? experiment.progress.training_set);
  }, [experiment]);

  const effectiveReactionScopeAcknowledged =
    reactionScopeAcknowledged ?? experiment?.progress.reaction_scope ?? false;
  const effectiveTrainingAcknowledged =
    trainingAcknowledged ?? experiment?.progress.training_set ?? false;

  const showReactionScope = Boolean(
    experiment &&
      (!experiment.progress.reaction_scope || !effectiveReactionScopeAcknowledged),
  );
  const showTraining = Boolean(
    experiment?.progress.reaction_scope &&
      effectiveReactionScopeAcknowledged &&
      experiment.mode === 'new' &&
      (!experiment.progress.training_set || !effectiveTrainingAcknowledged),
  );
  const showPrediction = Boolean(
    experiment?.progress.reaction_scope &&
      effectiveReactionScopeAcknowledged &&
      (experiment.mode === 'old' ||
        (experiment.progress.training_set && effectiveTrainingAcknowledged)) &&
      !experiment.progress.optimization,
  );

  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header p="md">
        <Group justify="space-between">
          <Stack gap={0}>
            <Title order={4}>{experimentId}</Title>
            {experiment && (
              <Text size="xs" c="dimmed">
                {experiment.exp_dir}
              </Text>
            )}
          </Stack>
          <Anchor component={Link} to="/">
            All experiments
          </Anchor>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="lg">
          {isPending && <Loader />}
          {isError && <Alert color="red">{error.message}</Alert>}
          {experiment && (
            <>
              <Stepper
                active={activeStep(
                  experiment.mode,
                  experiment.progress,
                  effectiveReactionScopeAcknowledged,
                  effectiveTrainingAcknowledged,
                )}
                mb="xl"
              >
                <Stepper.Step label="Reaction scope" description="Define the space" />
                {experiment.mode === 'new' && (
                  <Stepper.Step label="Training" description="Collect training data" />
                )}
                <Stepper.Step label="Prediction" description="Optimize" />
                <Stepper.Completed>Optimization complete</Stepper.Completed>
              </Stepper>

              {showReactionScope && (
                <ReactionScopeStep
                  experimentId={experiment.id}
                  mode={experiment.mode}
                  reactionScopeDone={experiment.progress.reaction_scope}
                  onContinue={() => setReactionScopeAcknowledged(true)}
                />
              )}
              {showTraining && (
                <TrainingStep
                  experimentId={experiment.id}
                  experiment={experiment}
                  onContinue={() => setTrainingAcknowledged(true)}
                />
              )}
              {showPrediction && (
                <PredictionStep experimentId={experiment.id} experiment={experiment} />
              )}
              {experiment.progress.optimization && (
                <CompletedStep experimentId={experiment.id} />
              )}
            </>
          )}
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
