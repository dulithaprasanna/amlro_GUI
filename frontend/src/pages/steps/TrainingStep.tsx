import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Group,
  Loader,
  NumberInput,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useTrainingInit, useTrainingNext, useTrainingTable } from '../../api/training';
import type { ExperimentState } from '../../api/types';

interface TrainingStepProps {
  experimentId: string;
  experiment: ExperimentState;
  onContinue: () => void;
}

export function TrainingStep({ experimentId, experiment, onContinue }: TrainingStepProps) {
  const table = useTrainingTable(experimentId);
  const trainingNext = useTrainingNext(experimentId);

  // AMLRO's generate_training_data only writes the reaction-data header the
  // very first time it's called, regardless of what's passed in — calling it
  // twice before that header exists silently drops whatever was submitted.
  // training_progress.parameters is only ever empty before that first call,
  // so it doubles as a safe "have we primed the loop yet?" flag.
  const needsInit =
    !experiment.progress.training_set && experiment.training_progress.parameters.length === 0;
  const trainingInit = useTrainingInit(experimentId, needsInit);

  const activeIndex = experiment.training_progress.current_iteration;
  const isComplete = experiment.progress.training_set;
  const [objValues, setObjValues] = useState<Record<number, number | ''>>({});

  if (trainingInit.isError && !isComplete) {
    return (
      <Alert color="red" title="Couldn't start the training loop">
        <Text mb="sm">{trainingInit.error.message}</Text>
        <Button size="xs" onClick={() => trainingInit.refetch()}>
          Retry
        </Button>
      </Alert>
    );
  }
  if ((needsInit || table.isPending) && !isComplete) {
    return (
      <Stack align="center" py="xl" gap="sm">
        <Loader />
        <Text c="dimmed">Loading the training plan...</Text>
      </Stack>
    );
  }
  if (table.isError) {
    return <Alert color="red">{table.error.message}</Alert>;
  }

  const data = table.data!;
  const currentRow = data.rows[activeIndex];

  const handleSubmit = () => {
    const values = data.objective_names.map((_, i) => objValues[i]);
    if (values.some((v) => v === '' || v === undefined)) {
      notifications.show({ message: 'Fill in every objective value.', color: 'red' });
      return;
    }
    trainingNext.mutate(values as number[], {
      onSuccess: () => setObjValues({}),
      onError: (error) => notifications.show({ message: error.message, color: 'red' }),
    });
  };

  return (
    <Stack gap="lg">
      <Title order={3}>Training — collect data</Title>

      <Card withBorder>
        {isComplete ? (
          <Stack align="center" py="md" gap="xs">
            <Title order={4}>Training set complete</Title>
            <Text c="dimmed">
              All {data.training_size} conditions have been recorded.
            </Text>
            <Button onClick={onContinue} mt="sm">
              Continue to prediction
            </Button>
          </Stack>
        ) : (
          <>
            <Title order={5} mb="sm">
              Condition {activeIndex + 1} of {data.training_size}
            </Title>
            {currentRow && (
              <Table withTableBorder mb="md">
                <Table.Thead>
                  <Table.Tr>
                    {data.feature_names.map((f) => (
                      <Table.Th key={f}>{f}</Table.Th>
                    ))}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    {currentRow.parameters.map((value, i) => (
                      <Table.Td key={i}>{String(value)}</Table.Td>
                    ))}
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            )}

            <Stack gap="xs" mb="md">
              {data.objective_names.map((name, i) => (
                <NumberInput
                  key={name}
                  label={name}
                  value={objValues[i] ?? ''}
                  onChange={(value) =>
                    setObjValues((prev) => ({
                      ...prev,
                      [i]: value === '' ? '' : Number(value),
                    }))
                  }
                />
              ))}
            </Stack>

            <Group justify="flex-end">
              <Button onClick={handleSubmit} loading={trainingNext.isPending}>
                Submit and get next condition
              </Button>
            </Group>
          </>
        )}
      </Card>

      <Card withBorder>
        <Title order={5} mb="sm">
          All training conditions
        </Title>
        <Table withTableBorder striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              {data.feature_names.map((f) => (
                <Table.Th key={f}>{f}</Table.Th>
              ))}
              {data.objective_names.map((o) => (
                <Table.Th key={o}>{o}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.rows.map((row) => (
              <Table.Tr key={row.iteration}>
                <Table.Td>{row.iteration + 1}</Table.Td>
                {row.parameters.map((value, i) => (
                  <Table.Td key={i}>{String(value)}</Table.Td>
                ))}
                {data.objective_names.map((_, i) => (
                  <Table.Td key={i}>
                    {row.status === 'completed' ? String(row.objectives?.[i]) : ''}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  );
}
