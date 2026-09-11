import { useEffect, useState } from 'react';
import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { ObjectiveTrajectoryChart } from '../../components/ObjectiveTrajectoryChart';
import { useFullDataset } from '../../api/dataset';
import {
  useCurrentBatch,
  usePredictionNext,
  useUpdateBatchSize,
} from '../../api/prediction';
import type { ExperimentState } from '../../api/types';

interface BatchRow {
  parameters: (string | number)[];
  objectives: (number | '')[];
  source: 'predicted' | 'manual';
}

interface PredictionStepProps {
  experimentId: string;
  experiment: ExperimentState;
}

export function PredictionStep({ experimentId, experiment }: PredictionStepProps) {
  const config = experiment.config!;
  const featureNames = [
    ...config.continuous.feature_names,
    ...config.categorical.feature_names,
  ];
  const objectiveNames = config.objectives;
  const continuousCount = config.continuous.feature_names.length;

  const predictionNext = usePredictionNext(experimentId);
  const updateBatchSize = useUpdateBatchSize(experimentId);
  const fullDataset = useFullDataset(experimentId);
  const [batch, setBatch] = useState<BatchRow[] | null>(null);
  const [batchSize, setBatchSize] = useState(experiment.batch_size);
  const [rowPendingRemoval, setRowPendingRemoval] = useState<number | null>(null);

  const handleUpdateBatchSize = () => {
    updateBatchSize.mutate(batchSize, {
      // Discard whatever's currently shown (including any values the user
      // had started filling in) and force a fresh, correctly-sized batch —
      // the whole point of changing this is to get a different-sized batch.
      onSuccess: () => setBatch(null),
      onError: (error) => notifications.show({ message: error.message, color: 'red' }),
    });
  };

  const blankObjectives = (): (number | '')[] => objectiveNames.map(() => '');

  const applyPredictedBatch = (parameters: unknown[][]) => {
    setBatch(
      parameters.map((row) => ({
        parameters: row as (string | number)[],
        objectives: blankObjectives(),
        source: 'predicted',
      })),
    );
  };

  // Fetches the currently-recommended batch whenever we don't have one
  // locally — covers both the very first cycle and reloading/returning to
  // this experiment mid-cycle (AMLRO's models are seeded/reproducible, so
  // re-fetching gives back the same batch rather than a new one).
  const needsFetch = batch === null;
  const currentBatch = useCurrentBatch(
    experimentId,
    experiment.prediction_progress.current_iteration,
    needsFetch,
  );

  useEffect(() => {
    if (currentBatch.isSuccess && currentBatch.data && batch === null) {
      applyPredictedBatch(currentBatch.data.parameters);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBatch.isSuccess, currentBatch.data]);

  if (currentBatch.isError && batch === null) {
    return (
      <Alert color="red" title="Couldn't train the prediction model">
        <Text mb="sm">{currentBatch.error.message}</Text>
        <Button size="xs" onClick={() => currentBatch.refetch()}>
          Retry
        </Button>
      </Alert>
    );
  }
  if (needsFetch || batch === null) {
    return (
      <Stack align="center" py="xl" gap="sm">
        <Loader />
        <Title order={4}>Training the prediction model...</Title>
        <Text c="dimmed" ta="center" maw={420}>
          Fitting a model on the training data collected so far and generating
          the first batch of conditions to try. This can take anywhere from a
          few seconds to about a minute depending on how much data there is.
        </Text>
      </Stack>
    );
  }

  const addRow = () => {
    setBatch([
      ...batch,
      {
        parameters: featureNames.map(() => ''),
        objectives: blankObjectives(),
        source: 'manual',
      },
    ]);
  };

  const confirmRemoveRow = () => {
    if (rowPendingRemoval === null) return;
    setBatch(batch.filter((_, i) => i !== rowPendingRemoval));
    setRowPendingRemoval(null);
  };

  const updateParameter = (rowIndex: number, colIndex: number, value: string) => {
    setBatch(
      batch.map((row, i) =>
        i === rowIndex
          ? {
              ...row,
              parameters: row.parameters.map((v, j) => (j === colIndex ? value : v)),
            }
          : row,
      ),
    );
  };

  const updateObjective = (rowIndex: number, objIndex: number, value: number | '') => {
    setBatch(
      batch.map((row, i) =>
        i === rowIndex
          ? {
              ...row,
              objectives: row.objectives.map((v, j) => (j === objIndex ? value : v)),
            }
          : row,
      ),
    );
  };

  const validate = (stop: boolean): boolean => {
    // Stopping with no remaining conditions is fine — it means the user
    // removed everything AMLRO suggested and just wants to finalize.
    // Continuing needs at least one condition, since there'd be nothing
    // new to learn from otherwise.
    if (batch.length === 0) {
      if (stop) return true;
      notifications.show({ message: 'Add at least one reaction condition.', color: 'red' });
      return false;
    }
    for (const row of batch) {
      if (row.parameters.some((v) => v === '')) {
        notifications.show({ message: 'Fill in every parameter value.', color: 'red' });
        return false;
      }
      if (row.objectives.some((v) => v === '')) {
        notifications.show({ message: 'Fill in every objective value.', color: 'red' });
        return false;
      }
      // Rows AMLRO predicted are always in scope and aren't editable here —
      // only hand-added/edited rows can drift outside the configured
      // reaction space, so only those need checking.
      if (row.source === 'manual') {
        for (let i = 0; i < continuousCount; i++) {
          const [low, high] = config.continuous.bounds[i];
          const value = Number(row.parameters[i]);
          if (value < low || value > high) {
            notifications.show({
              message: `'${featureNames[i]}' must be between ${low} and ${high}.`,
              color: 'red',
            });
            return false;
          }
        }
        for (let i = continuousCount; i < featureNames.length; i++) {
          const allowed = config.categorical.values[i - continuousCount];
          if (!allowed.includes(String(row.parameters[i]))) {
            notifications.show({
              message: `'${featureNames[i]}' must be one of: ${allowed.join(', ')}.`,
              color: 'red',
            });
            return false;
          }
        }
      }
    }
    return true;
  };

  const submit = (stop: boolean) => {
    if (!validate(stop)) return;

    const parameters = batch.map((row) =>
      row.parameters.map((v) => (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v)) ? Number(v) : v)),
    );
    const objectives = batch.map((row) => row.objectives as number[]);

    predictionNext.mutate(
      { parameters, objectives, stop, batch_size: batchSize },
      {
        onSuccess: (result) => {
          if (!result.complete) {
            applyPredictedBatch(result.parameters ?? []);
          }
        },
        onError: (error) => notifications.show({ message: error.message, color: 'red' }),
      },
    );
  };

  return (
    <Stack gap="lg">
      <Title order={3}>
        Prediction cycle {experiment.prediction_progress.current_iteration + 1}
      </Title>

      <Group align="flex-end">
        <NumberInput
          label="Batch size"
          min={1}
          value={batchSize}
          onChange={(value) => setBatchSize(Number(value) || 1)}
          w={140}
        />
        <Button
          variant="light"
          onClick={handleUpdateBatchSize}
          loading={updateBatchSize.isPending}
          disabled={batchSize === experiment.batch_size}
        >
          Update batch size
        </Button>
      </Group>

      <Table withTableBorder striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>#</Table.Th>
            {featureNames.map((f) => (
              <Table.Th key={f}>{f}</Table.Th>
            ))}
            {objectiveNames.map((o) => (
              <Table.Th key={o}>{o}</Table.Th>
            ))}
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {batch.map((row, rowIndex) => (
            <Table.Tr key={rowIndex}>
              <Table.Td>{rowIndex + 1}</Table.Td>
              {row.parameters.map((value, colIndex) => (
                <Table.Td key={colIndex}>
                  {row.source === 'predicted' ? (
                    String(value)
                  ) : colIndex < continuousCount ? (
                    <NumberInput
                      size="xs"
                      value={value === '' ? '' : Number(value)}
                      onChange={(v) => updateParameter(rowIndex, colIndex, String(v))}
                      min={config.continuous.bounds[colIndex][0]}
                      max={config.continuous.bounds[colIndex][1]}
                    />
                  ) : (
                    <Select
                      size="xs"
                      data={config.categorical.values[colIndex - continuousCount]}
                      value={String(value) || null}
                      onChange={(v) => updateParameter(rowIndex, colIndex, v ?? '')}
                    />
                  )}
                </Table.Td>
              ))}
              {row.objectives.map((value, objIndex) => (
                <Table.Td key={objIndex}>
                  <NumberInput
                    size="xs"
                    value={value}
                    onChange={(v) => updateObjective(rowIndex, objIndex, v === '' ? '' : Number(v))}
                  />
                </Table.Td>
              ))}
              <Table.Td>
                <ActionIcon
                  color="red"
                  variant="light"
                  onClick={() => setRowPendingRemoval(rowIndex)}
                >
                  ×
                </ActionIcon>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Group justify="space-between">
        <Button variant="light" onClick={addRow}>
          Add reaction condition
        </Button>
        <Group>
          <Button
            color="gray"
            onClick={() => submit(true)}
            loading={predictionNext.isPending}
          >
            Stop optimization
          </Button>
          <Button
            onClick={() => submit(false)}
            loading={predictionNext.isPending}
            disabled={batch.length === 0}
          >
            Predict next conditions
          </Button>
        </Group>
      </Group>

      <Stack gap="md" mt="lg">
        <Title order={4}>Dataset so far</Title>

        <Box>
          <Text size="sm" fw={500} mb={4}>
            Objective trajectory
          </Text>
          {fullDataset.isPending ? (
            <Text c="dimmed" size="sm">
              Loading...
            </Text>
          ) : fullDataset.isError ? (
            <Alert color="red">{fullDataset.error.message}</Alert>
          ) : (
            <ObjectiveTrajectoryChart
              objectiveNames={fullDataset.data.objective_names}
              columns={fullDataset.data.columns}
              rows={fullDataset.data.rows}
            />
          )}
        </Box>

        <Box>
          <Text size="sm" fw={500} mb={4}>
            Full dataset ({fullDataset.data?.rows.length ?? 0} conditions)
          </Text>
          {fullDataset.data && fullDataset.data.rows.length > 0 ? (
            <Table.ScrollContainer minWidth={400} mah={320} style={{ overflowY: 'auto' }}>
              <Table withTableBorder striped stickyHeader>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>#</Table.Th>
                    {fullDataset.data.columns.map((col) => (
                      <Table.Th key={col}>{col}</Table.Th>
                    ))}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {fullDataset.data.rows.map((row, rowIndex) => (
                    <Table.Tr key={rowIndex}>
                      <Table.Td>{rowIndex}</Table.Td>
                      {row.map((value, colIndex) => (
                        <Table.Td key={colIndex}>{String(value)}</Table.Td>
                      ))}
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          ) : (
            !fullDataset.isPending &&
            !fullDataset.isError && (
              <Text c="dimmed" size="sm">
                No reaction conditions recorded yet.
              </Text>
            )
          )}
        </Box>
      </Stack>

      <Modal
        opened={rowPendingRemoval !== null}
        onClose={() => setRowPendingRemoval(null)}
        title="Remove this reaction condition?"
        centered
      >
        <Text mb="md">
          This only removes it from the batch you're about to submit — it
          won't affect any data already recorded.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setRowPendingRemoval(null)}>
            Cancel
          </Button>
          <Button color="red" onClick={confirmRemoveRow}>
            Remove
          </Button>
        </Group>
      </Modal>
    </Stack>
  );
}
