import { useState } from 'react';
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Code,
  Container,
  Group,
  Modal,
  Pagination,
  Paper,
  SegmentedControl,
  SimpleGrid,
  Spoiler,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useNavigate } from 'react-router-dom';
import amlroWorkflow from '../assets/amlro_workflow.jpg';
import {
  useCreateExperiment,
  useExperiments,
  useRemoveExperiment,
  useScanForExperiments,
} from '../api/experiments';
import type { ExperimentMode, ExperimentSummary, Progress } from '../api/types';

const PAGE_SIZES = [5, 10] as const;

// "old" mode (existing data) skips the training step entirely — it goes
// straight from reaction scope to prediction — so progress.training_set
// never becomes true for it. Mode-blind logic would otherwise show
// "Training" forever for an "old" mode experiment that's actually predicting.
function progressLabel(mode: ExperimentMode, progress: Progress): string {
  if (progress.optimization) return 'Optimization complete';
  if (mode === 'old') return progress.reaction_scope ? 'Predicting' : 'Just started';
  if (progress.training_set) return 'Predicting';
  if (progress.reaction_scope) return 'Training';
  return 'Just started';
}

function progressColor(mode: ExperimentMode, progress: Progress): string {
  if (progress.optimization) return 'teal';
  if (mode === 'old') return progress.reaction_scope ? 'blue' : 'gray';
  if (progress.training_set) return 'blue';
  if (progress.reaction_scope) return 'indigo';
  return 'gray';
}

export function LandingPage() {
  const navigate = useNavigate();
  const { data: experiments, isPending, isError } = useExperiments();
  const createExperiment = useCreateExperiment();
  const removeExperiment = useRemoveExperiment();
  const scanForExperiments = useScanForExperiments();

  const [mode, setMode] = useState<ExperimentMode>('new');
  const [id, setId] = useState('');
  const [expDir, setExpDir] = useState('');

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZES)[number]>(10);
  const [removeTarget, setRemoveTarget] = useState<ExperimentSummary | null>(null);
  const [deleteFilesToo, setDeleteFilesToo] = useState(false);
  const [scanRoot, setScanRoot] = useState('');

  const handleCreate = () => {
    createExperiment.mutate(
      { mode, id: id.trim() || undefined, exp_dir: expDir.trim() || undefined },
      {
        onSuccess: (state) => navigate(`/experiments/${state.id}`),
      },
    );
  };

  // experiments is already sorted most-recently-updated-first by the
  // backend — this just slices a page out of it.
  const totalPages = Math.max(1, Math.ceil((experiments?.length ?? 0) / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageItems = experiments?.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize,
  );

  const handlePageSizeChange = (size: (typeof PAGE_SIZES)[number]) => {
    setPageSize(size);
    setPage(1);
  };

  const closeRemoveModal = () => {
    setRemoveTarget(null);
    setDeleteFilesToo(false);
  };

  const confirmRemove = () => {
    if (!removeTarget) return;
    removeExperiment.mutate(
      { id: removeTarget.id, deleteFiles: deleteFilesToo },
      {
        onSuccess: () => {
          notifications.show({
            message: deleteFilesToo
              ? `'${removeTarget.id}' removed and its files deleted.`
              : `'${removeTarget.id}' removed from this list (files kept on disk).`,
            color: 'green',
          });
          closeRemoveModal();
        },
        onError: (error) => notifications.show({ message: error.message, color: 'red' }),
      },
    );
  };

  const handleScan = () => {
    if (!scanRoot.trim()) return;
    scanForExperiments.mutate(scanRoot.trim(), {
      onSuccess: (result) => {
        const parts = [`${result.added.length} experiment(s) added.`];
        if (result.skipped.length > 0) {
          parts.push(`${result.skipped.length} skipped (already known or id conflict).`);
        }
        notifications.show({ message: parts.join(' '), color: 'green' });
      },
      onError: (error) => notifications.show({ message: error.message, color: 'red' }),
    });
  };

  return (
    <Container size="lg" py="xl">
      <Stack gap="xl">
        <Paper radius="lg" p="xl" withBorder>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xl" verticalSpacing="lg">
            <Stack justify="center" gap={4}>
              <Text
                component="h1"
                fz={36}
                fw={800}
                variant="gradient"
                gradient={{ from: 'blue', to: 'cyan', deg: 90 }}
                style={{ margin: 0 }}
              >
                🧪 AMLRO
              </Text>
              <Text size="lg" fw={500}>
                Active Machine Learning Reaction Optimizer
              </Text>
              <Text size="sm" c="dimmed" maw={480}>
                Data-efficient reaction condition discovery and optimization, powered by
                active learning.
              </Text>
              <Group gap="sm" mt="md">
                <Button
                  component="a"
                  href="https://rxnrover.github.io/amlro/"
                  target="_blank"
                  variant="light"
                >
                  📘 Documentation
                </Button>
                <Button
                  component="a"
                  href="https://github.com/RxnRover/amlro"
                  target="_blank"
                  variant="light"
                >
                  GitHub
                </Button>
                <Button
                  component="a"
                  href="https://colab.research.google.com/github/RxnRover/amlro/blob/main/notebooks/AMLRO_interactive_colab.ipynb"
                  target="_blank"
                  variant="light"
                >
                  Colab notebook
                </Button>
              </Group>
            </Stack>

            <img
              src={amlroWorkflow}
              alt="AMLRO: Active Machine Learning Reaction Optimizer — a cycle of defining the reaction space, selecting initial data, model training and prediction, and experimental feedback that re-trains the model"
              style={{ width: '100%', maxWidth: 360, justifySelf: 'center' }}
            />
          </SimpleGrid>

          <Spoiler
            maxHeight={0}
            showLabel="More about AMLRO"
            hideLabel="Show less"
            mt="lg"
            style={{ textAlign: 'center', width: '100%' }}
          >
            <Stack gap="sm" ta="left" maw={640} mx="auto">
              <Text size="sm">
                AMLRO is an open-source framework designed to accelerate chemical
                reaction optimization using active learning with classical machine
                learning regression models. It integrates space-filling sampling
                strategies (Sobol, Latin Hypercube) with iterative model training,
                prediction, and experiment selection to efficiently navigate complex
                reaction spaces — supporting multiple regression models, multi-objective
                definitions, and user-defined parameter bounds, enabling data-efficient
                optimization from small initial datasets.
              </Text>
              <div>
                <Text size="sm" fw={500} mb={4}>
                  Citation
                </Text>
                <Text size="sm">
                  Kulathunga, D. P. et al. <i>RxnRover/amlro</i>. Computer Software.
                  USDOE Office of Energy Efficiency and Renewable Energy (EERE),
                  Advanced Materials & Manufacturing Technologies Office (AMMTO), 2026.
                  DOI:{' '}
                  <a
                    href="https://doi.org/10.11578/dc.20260205.1"
                    target="_blank"
                    rel="noreferrer"
                  >
                    10.11578/dc.20260205.1
                  </a>
                </Text>
              </div>
              <Code block>
                {`@misc{doecode_174798,
  title        = {RxnRover/amlro},
  author       = {Kulathunga, Dulitha Prasanna and Crandall, Zachery},
  doi          = {10.11578/dc.20260205.1},
  url          = {https://doi.org/10.11578/dc.20260205.1},
  howpublished = {[Computer Software] \\url{https://doi.org/10.11578/dc.20260205.1}},
  year         = {2026},
  month        = {feb}
}`}
              </Code>
            </Stack>
          </Spoiler>
        </Paper>

        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl">
          <Card withBorder padding="lg" radius="md">
            <Stack gap="sm">
              <Title order={4}>Start new experiment</Title>
              <SegmentedControl
                value={mode}
                onChange={(value) => setMode(value as ExperimentMode)}
                fullWidth
                data={[
                  { label: 'New reaction scope', value: 'new' },
                  { label: 'Use existing data', value: 'old' },
                ]}
              />
              <TextInput
                label="Experiment name (optional)"
                placeholder="e.g. suzuki-coupling-run-1"
                value={id}
                onChange={(event) => setId(event.currentTarget.value)}
              />
              <TextInput
                label="Save to folder (optional)"
                description="Leave blank to use the default workspace folder"
                placeholder="e.g. D:\Reactions\suzuki-coupling-run-1"
                value={expDir}
                onChange={(event) => setExpDir(event.currentTarget.value)}
              />
              {createExperiment.isError && (
                <Alert color="red">{createExperiment.error.message}</Alert>
              )}
              <Group justify="flex-end">
                <Button onClick={handleCreate} loading={createExperiment.isPending}>
                  Create
                </Button>
              </Group>
            </Stack>
          </Card>

          <Card withBorder padding="lg" radius="md">
            <Stack gap="sm">
              <Group justify="space-between">
                <Title order={4}>Resume an experiment</Title>
                {experiments && experiments.length > 0 && (
                  <SegmentedControl
                    size="xs"
                    value={String(pageSize)}
                    onChange={(value) =>
                      handlePageSizeChange(Number(value) as (typeof PAGE_SIZES)[number])
                    }
                    data={PAGE_SIZES.map((size) => ({
                      label: `${size}/page`,
                      value: String(size),
                    }))}
                  />
                )}
              </Group>

              {isPending && <Text c="dimmed">Loading...</Text>}
              {isError && <Alert color="red">Could not load experiments.</Alert>}
              {experiments?.length === 0 && (
                <Text c="dimmed">No experiments yet — create one to get started.</Text>
              )}

              <Stack gap="xs">
                {pageItems?.map((experiment) => (
                  <Card
                    key={experiment.id}
                    withBorder
                    padding="sm"
                    radius="sm"
                    onClick={() => navigate(`/experiments/${experiment.id}`)}
                    style={{ textAlign: 'left', cursor: 'pointer' }}
                  >
                    <Group justify="space-between" wrap="nowrap">
                      <div style={{ minWidth: 0 }}>
                        <Text fw={500} truncate>
                          {experiment.id}
                        </Text>
                        <Text size="xs" c="dimmed" truncate>
                          {experiment.mode === 'new'
                            ? 'New reaction scope'
                            : 'Existing data'}
                          {' — '}
                          {experiment.exp_dir}
                        </Text>
                        <Text size="xs" c="dimmed" truncate>
                          Updated {new Date(experiment.updated_at).toLocaleString()}
                        </Text>
                      </div>
                      <Group gap="xs" wrap="nowrap">
                        <Badge color={progressColor(experiment.mode, experiment.progress)}>
                          {progressLabel(experiment.mode, experiment.progress)}
                        </Badge>
                        <ActionIcon
                          color="red"
                          variant="subtle"
                          aria-label={`Remove ${experiment.id} from this list`}
                          onClick={(event) => {
                            event.stopPropagation();
                            setRemoveTarget(experiment);
                          }}
                        >
                          ×
                        </ActionIcon>
                      </Group>
                    </Group>
                  </Card>
                ))}
              </Stack>

              {totalPages > 1 && (
                <Group justify="center">
                  <Pagination total={totalPages} value={currentPage} onChange={setPage} />
                </Group>
              )}

              <Stack gap={4} mt="sm">
                <Text size="sm" fw={500}>
                  Find experiments already on disk
                </Text>
                <Text size="xs" c="dimmed">
                  Point to a folder containing experiment subfolders (each with its own
                  state.json) to add any not already shown above — useful if they were
                  copied in or created by a different workspace.
                </Text>
                <Group gap="xs">
                  <TextInput
                    placeholder="e.g. D:\Reactions"
                    value={scanRoot}
                    onChange={(event) => setScanRoot(event.currentTarget.value)}
                    style={{ flex: 1 }}
                  />
                  <Button
                    variant="light"
                    onClick={handleScan}
                    loading={scanForExperiments.isPending}
                    disabled={!scanRoot.trim()}
                  >
                    Scan
                  </Button>
                </Group>
              </Stack>
            </Stack>
          </Card>
        </SimpleGrid>
      </Stack>

      <Modal
        opened={removeTarget !== null}
        onClose={closeRemoveModal}
        title={`Remove '${removeTarget?.id}' from this list?`}
        centered
      >
        <Stack gap="sm">
          <Text size="sm">
            This only removes it from the landing page — it can be added back later by
            scanning its folder.
          </Text>
          <Checkbox
            label="Also permanently delete this experiment's files from disk"
            checked={deleteFilesToo}
            onChange={(event) => setDeleteFilesToo(event.currentTarget.checked)}
          />
          {deleteFilesToo && (
            <Alert color="red">
              This cannot be undone — every file in{' '}
              <b>{removeTarget?.exp_dir}</b> will be permanently deleted.
            </Alert>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={closeRemoveModal}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={confirmRemove}
              loading={removeExperiment.isPending}
            >
              {deleteFilesToo ? 'Remove and delete files' : 'Remove from list'}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
