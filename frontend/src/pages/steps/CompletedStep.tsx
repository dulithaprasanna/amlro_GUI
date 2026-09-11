import { Button, Group, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useNavigate } from 'react-router-dom';
import { useResumeOptimization } from '../../api/prediction';

interface CompletedStepProps {
  experimentId: string;
}

export function CompletedStep({ experimentId }: CompletedStepProps) {
  const navigate = useNavigate();
  const resumeOptimization = useResumeOptimization(experimentId);

  const handleResume = () => {
    resumeOptimization.mutate(undefined, {
      onError: (error) => notifications.show({ message: error.message, color: 'red' }),
    });
  };

  return (
    <Stack gap="sm" align="center" py="xl">
      <Title order={2}>Optimization complete</Title>
      <Text c="dimmed" ta="center" maw={420}>
        Results have been written to this experiment's directory
        (reactions_data.csv and next_batch.csv hold the full history and the
        last suggested batch).
      </Text>
      <Group mt="sm">
        <Button variant="default" onClick={() => navigate('/')}>
          Home
        </Button>
        <Button onClick={handleResume} loading={resumeOptimization.isPending}>
          Resume optimization
        </Button>
      </Group>
    </Stack>
  );
}
