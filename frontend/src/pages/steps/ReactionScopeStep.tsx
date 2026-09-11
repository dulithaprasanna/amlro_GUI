import {
  ActionIcon,
  Alert,
  Button,
  Card,
  FileButton,
  Group,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useCreateReactionScope } from '../../api/reactionScope';
import { useUploadReactionData } from '../../api/data';
import type {
  Direction,
  ExperimentConfig,
  ExperimentMode,
  SamplingMethod,
} from '../../api/types';

const REGRESSOR_OPTIONS = [
  { value: 'gb', label: 'Gradient Boosting' },
  { value: 'rf', label: 'Random Forest' },
  { value: 'xgb', label: 'XGBoost' },
  { value: 'ela_net', label: 'Elastic Net' },
  { value: 'dtree', label: 'Decision Tree' },
  { value: 'aboost', label: 'AdaBoost' },
  { value: 'svr', label: 'Support Vector Regressor' },
  { value: 'knn', label: 'K-Nearest Neighbors' },
  { value: 'bayesian_ridge', label: 'Bayesian Ridge' },
];

const SAMPLING_OPTIONS: { value: SamplingMethod; label: string }[] = [
  { value: 'random', label: 'Random' },
  { value: 'lhs', label: 'Latin Hypercube' },
  { value: 'sobol', label: 'Sobol Sequence' },
];

interface ContinuousRow {
  name: string;
  min: number | '';
  max: number | '';
  resolution: number | '';
}

interface CategoricalRow {
  name: string;
  values: string;
}

interface ObjectiveRow {
  name: string;
  direction: Direction;
}

interface FormValues {
  continuous: ContinuousRow[];
  categorical: CategoricalRow[];
  objectives: ObjectiveRow[];
  sampling: SamplingMethod;
  training_size: number;
  regresor_model: string;
  file_name: string;
  batch_size: number;
}

const initialValues: FormValues = {
  continuous: [],
  categorical: [],
  objectives: [],
  sampling: 'random',
  training_size: 10,
  regresor_model: 'gb',
  file_name: 'reactions_data.csv',
  batch_size: 1,
};

function configToFormValues(config: ExperimentConfig): FormValues {
  return {
    continuous: config.continuous.feature_names.map((name, i) => ({
      name,
      min: config.continuous.bounds[i][0],
      max: config.continuous.bounds[i][1],
      resolution: config.continuous.resolutions[i],
    })),
    categorical: config.categorical.feature_names.map((name, i) => ({
      name,
      values: config.categorical.values[i].join(', '),
    })),
    objectives: config.objectives.map((name, i) => ({
      name,
      direction: config.directions[i],
    })),
    sampling: config.sampling,
    training_size: config.training_size,
    regresor_model: config.regresor_model,
    file_name: config.file_name,
    batch_size: config.batch_size,
  };
}

function formValuesToConfig(values: FormValues): ExperimentConfig {
  return {
    continuous: {
      feature_names: values.continuous.map((row) => row.name),
      bounds: values.continuous.map((row) => [
        Number(row.min),
        Number(row.max),
      ]),
      resolutions: values.continuous.map((row) => Number(row.resolution)),
    },
    categorical: {
      feature_names: values.categorical.map((row) => row.name),
      values: values.categorical.map((row) =>
        row.values.split(',').map((v) => v.trim()).filter(Boolean),
      ),
    },
    objectives: values.objectives.map((row) => row.name),
    directions: values.objectives.map((row) => row.direction),
    sampling: values.sampling,
    training_size: values.training_size,
    regresor_model: values.regresor_model,
    file_name: values.file_name,
    batch_size: values.batch_size,
  };
}

interface ReactionScopeStepProps {
  experimentId: string;
  mode: ExperimentMode;
  reactionScopeDone: boolean;
  onContinue: () => void;
}

export function ReactionScopeStep({
  experimentId,
  mode,
  reactionScopeDone,
  onContinue,
}: ReactionScopeStepProps) {
  const createReactionScope = useCreateReactionScope(experimentId);
  const uploadData = useUploadReactionData(experimentId);

  const form = useForm<FormValues>({ initialValues });

  if (reactionScopeDone) {
    return (
      <Stack align="center" py="xl" gap="xs">
        <Title order={3}>Reaction scope generated successfully</Title>
        <Text c="dimmed" ta="center" maw={420}>
          The full reaction space and training conditions have been written to
          this experiment's folder.
        </Text>
        <Button onClick={onContinue} mt="sm">
          {mode === 'new' ? 'Continue to training' : 'Continue to prediction'}
        </Button>
      </Stack>
    );
  }

  const handleLoadConfig = async (file: File | null) => {
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as ExperimentConfig;
      form.setValues(configToFormValues(parsed));
      notifications.show({ message: 'Configuration loaded from file.', color: 'green' });
    } catch {
      notifications.show({
        message: 'Could not read that file as a valid configuration.',
        color: 'red',
      });
    }
  };

  const handleUpload = (file: File | null) => {
    if (!file) return;
    // Must be the same name submitted as config.file_name — the backend
    // looks for the upload at exactly that path when generating the
    // reaction space. A separate, disconnected "save as" field here would
    // let the two silently drift apart.
    const fileName = form.values.file_name || 'reactions_data.csv';
    uploadData.mutate(
      { file, fileName },
      {
        onError: (error) =>
          notifications.show({ message: error.message, color: 'red' }),
      },
    );
  };

  const handleSubmit = (values: FormValues) => {
    if (values.continuous.length === 0 && values.categorical.length === 0) {
      notifications.show({
        message: 'Add at least one continuous or categorical feature.',
        color: 'red',
      });
      return;
    }
    if (values.objectives.length === 0) {
      notifications.show({ message: 'Add at least one objective.', color: 'red' });
      return;
    }

    createReactionScope.mutate(formValuesToConfig(values), {
      onError: (error) => notifications.show({ message: error.message, color: 'red' }),
    });
  };

  // Expected column order matches how AMLRO itself lays out the reaction
  // data file (continuous features, then categorical, then objectives) —
  // getting this wrong doesn't just fail loudly: pandas' name-based
  // train[cols]/train.drop(cols) calls would still separate x/y correctly,
  // but the resulting feature column order could silently mismatch
  // full_combo.csv's generation order, since the sklearn models underneath
  // fit/predict positionally, not by column name.
  const expectedColumns = [
    ...form.values.continuous.map((row) => row.name),
    ...form.values.categorical.map((row) => row.name),
    ...form.values.objectives.map((row) => row.name),
  ];
  const columnsMatch =
    uploadData.data &&
    expectedColumns.length > 0 &&
    expectedColumns.every((name, i) => uploadData.data!.columns[i] === name) &&
    uploadData.data.columns.length === expectedColumns.length;

  return (
    <Stack gap="lg">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="lg">
          <Group justify="space-between">
            <Title order={3}>Reaction scope configuration</Title>
            <FileButton onChange={handleLoadConfig} accept="application/json">
              {(props) => <Button {...props} variant="light">Load config from file</Button>}
            </FileButton>
          </Group>

          <Card withBorder>
            <Title order={4} mb="sm">Continuous features</Title>
            <Stack gap="xs">
              {form.values.continuous.map((_, index) => (
                <Group key={index} align="flex-end">
                  <TextInput
                    label="Name"
                    placeholder="Temperature"
                    {...form.getInputProps(`continuous.${index}.name`)}
                  />
                  <NumberInput
                    label="Min"
                    {...form.getInputProps(`continuous.${index}.min`)}
                  />
                  <NumberInput
                    label="Max"
                    {...form.getInputProps(`continuous.${index}.max`)}
                  />
                  <NumberInput
                    label="Resolution"
                    {...form.getInputProps(`continuous.${index}.resolution`)}
                  />
                  <ActionIcon
                    color="red"
                    variant="light"
                    onClick={() => form.removeListItem('continuous', index)}
                  >
                    ×
                  </ActionIcon>
                </Group>
              ))}
            </Stack>
            <Button
              mt="sm"
              variant="light"
              onClick={() =>
                form.insertListItem('continuous', {
                  name: '',
                  min: '',
                  max: '',
                  resolution: '',
                })
              }
            >
              Add continuous feature
            </Button>
          </Card>

          <Card withBorder>
            <Title order={4} mb="sm">Categorical features</Title>
            <Stack gap="xs">
              {form.values.categorical.map((_, index) => (
                <Group key={index} align="flex-end">
                  <TextInput
                    label="Name"
                    placeholder="Solvent"
                    {...form.getInputProps(`categorical.${index}.name`)}
                  />
                  <TextInput
                    label="Values (comma-separated)"
                    placeholder="A, B, C"
                    w={280}
                    {...form.getInputProps(`categorical.${index}.values`)}
                  />
                  <ActionIcon
                    color="red"
                    variant="light"
                    onClick={() => form.removeListItem('categorical', index)}
                  >
                    ×
                  </ActionIcon>
                </Group>
              ))}
            </Stack>
            <Button
              mt="sm"
              variant="light"
              onClick={() =>
                form.insertListItem('categorical', { name: '', values: '' })
              }
            >
              Add categorical feature
            </Button>
          </Card>

          <Card withBorder>
            <Title order={4} mb="sm">Objectives</Title>
            <Stack gap="xs">
              {form.values.objectives.map((_, index) => (
                <Group key={index} align="flex-end">
                  <TextInput
                    label="Name"
                    placeholder="Yield"
                    {...form.getInputProps(`objectives.${index}.name`)}
                  />
                  <Select
                    label="Direction"
                    data={[
                      { value: 'max', label: 'Maximize' },
                      { value: 'min', label: 'Minimize' },
                    ]}
                    {...form.getInputProps(`objectives.${index}.direction`)}
                  />
                  <ActionIcon
                    color="red"
                    variant="light"
                    onClick={() => form.removeListItem('objectives', index)}
                  >
                    ×
                  </ActionIcon>
                </Group>
              ))}
            </Stack>
            <Button
              mt="sm"
              variant="light"
              onClick={() =>
                form.insertListItem('objectives', { name: '', direction: 'max' })
              }
            >
              Add objective
            </Button>
          </Card>

          <Card withBorder>
            <Title order={4} mb="sm">Other settings</Title>
            <Group grow>
              <Select
                label="Sampling method"
                data={SAMPLING_OPTIONS}
                {...form.getInputProps('sampling')}
              />
              <NumberInput
                label="Training size"
                min={1}
                {...form.getInputProps('training_size')}
              />
              <Select
                label="Regressor model"
                data={REGRESSOR_OPTIONS}
                {...form.getInputProps('regresor_model')}
              />
            </Group>
            <Group grow mt="sm">
              <TextInput label="File name" {...form.getInputProps('file_name')} />
              <NumberInput
                label="Batch size"
                min={1}
                {...form.getInputProps('batch_size')}
              />
            </Group>
          </Card>

          {mode === 'old' && (
            <Card withBorder>
              <Title order={4} mb="sm">
                Upload existing reaction data
              </Title>
              <Text size="sm" c="dimmed" mb="sm">
                Upload the CSV of reactions you've already run. Its columns
                must be, in order: your continuous feature names, then
                categorical feature names, then objective names, matching
                what you configured above. Categorical columns may be
                either the actual category names or their encoded
                0/1/2... index — but not a mix of both across columns.
              </Text>
              <Text size="sm" mb="sm">
                Will be saved as <b>{form.values.file_name || 'reactions_data.csv'}</b>{' '}
                (change "File name" above to use a different name).
              </Text>
              <FileButton onChange={handleUpload} accept=".csv">
                {(props) => (
                  <Button {...props} loading={uploadData.isPending}>
                    Choose CSV and upload
                  </Button>
                )}
              </FileButton>
              {uploadData.data && (
                <>
                  <Alert color={columnsMatch ? 'green' : 'yellow'} mt="sm">
                    {columnsMatch
                      ? 'Column names and order match your configuration above.'
                      : `Expected columns (in order): ${expectedColumns.join(', ') || '(configure features/objectives above first)'}. Found: ${uploadData.data.columns.join(', ')}. Generating the reaction space will be blocked until these match.`}
                  </Alert>
                  <Table mt="sm" withTableBorder striped>
                    <Table.Thead>
                      <Table.Tr>
                        {uploadData.data.columns.map((col) => (
                          <Table.Th key={col}>{col}</Table.Th>
                        ))}
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {uploadData.data.preview.map((row, i) => (
                        <Table.Tr key={i}>
                          {uploadData.data!.columns.map((col) => (
                            <Table.Td key={col}>{String(row[col])}</Table.Td>
                          ))}
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </>
              )}
            </Card>
          )}

          {createReactionScope.isError && (
            <Alert color="red">{createReactionScope.error.message}</Alert>
          )}

          <Button type="submit" size="lg" loading={createReactionScope.isPending}>
            Generate reaction space
          </Button>
        </Stack>
      </form>
    </Stack>
  );
}
