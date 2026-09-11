import { ResponsiveLine } from '@nivo/line';
import { Box, Group, Text } from '@mantine/core';

// Validated categorical palette (light mode), fixed slot order — see the
// dataviz skill's references/palette.md. Objectives are few (typically
// 1-4), well inside the slots validated for adjacent-pair CVD safety.
const SERIES_COLORS = [
  '#2a78d6', // blue
  '#eb6834', // orange
  '#1baf7a', // aqua
  '#eda100', // yellow
  '#e87ba4', // magenta
  '#008300', // green
  '#4a3aa7', // violet
  '#e34948', // red
];

const CHROME = {
  surface: '#fcfcfb',
  textSecondary: '#52514e',
  muted: '#898781',
  gridline: '#e1e0d9',
  baseline: '#c3c2b7',
};

interface ObjectiveTrajectoryChartProps {
  objectiveNames: string[];
  columns: string[];
  rows: (string | number)[][];
}

export function ObjectiveTrajectoryChart({
  objectiveNames,
  columns,
  rows,
}: ObjectiveTrajectoryChartProps) {
  if (rows.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        No reaction conditions recorded yet — this chart fills in as training
        and prediction results come in.
      </Text>
    );
  }

  const objectiveStartIndex = columns.length - objectiveNames.length;
  const series = objectiveNames.map((name, i) => ({
    id: name,
    data: rows.map((row, rowIndex) => ({
      x: rowIndex,
      y: Number(row[objectiveStartIndex + i]),
    })),
  }));

  const colors = SERIES_COLORS.slice(0, objectiveNames.length);

  return (
    <Box>
      {objectiveNames.length > 1 && (
        <Group gap="md" mb="xs">
          {objectiveNames.map((name, i) => (
            <Group key={name} gap={6} wrap="nowrap">
              <Box
                w={10}
                h={10}
                style={{ borderRadius: 2, background: colors[i], flexShrink: 0 }}
              />
              <Text size="xs" c="dimmed">
                {name}
              </Text>
            </Group>
          ))}
        </Group>
      )}
      <Box h={320}>
        <ResponsiveLine
          data={series}
          colors={colors}
          margin={{ top: 16, right: 24, bottom: 50, left: 56 }}
          xScale={{ type: 'point' }}
          yScale={{ type: 'linear', min: 'auto', max: 'auto', nice: true }}
          lineWidth={2}
          pointSize={8}
          pointBorderWidth={2}
          pointBorderColor={{ from: 'serieColor' }}
          pointColor={CHROME.surface}
          enablePoints
          enableGridX={false}
          gridYValues={5}
          theme={{
            grid: { line: { stroke: CHROME.gridline, strokeWidth: 1 } },
            axis: {
              ticks: {
                text: { fill: CHROME.muted, fontSize: 11 },
                line: { stroke: CHROME.baseline },
              },
              legend: { text: { fill: CHROME.textSecondary, fontSize: 12 } },
              domain: { line: { stroke: CHROME.baseline, strokeWidth: 1 } },
            },
            crosshair: { line: { stroke: CHROME.muted, strokeWidth: 1 } },
          }}
          axisBottom={{
            legend: 'Recorded condition #',
            legendOffset: 36,
            legendPosition: 'middle',
            tickValues: rows.length > 12 ? undefined : rows.map((_, i) => i),
          }}
          axisLeft={{
            legend:
              objectiveNames.length === 1 ? objectiveNames[0] : 'Objective value',
            legendOffset: -44,
            legendPosition: 'middle',
          }}
          enableSlices="x"
          sliceTooltip={({ slice }) => (
            <Box
              style={{
                background: CHROME.surface,
                border: `1px solid ${CHROME.gridline}`,
                borderRadius: 4,
                padding: '6px 10px',
                boxShadow: '0 1px 4px rgba(11,11,11,0.12)',
              }}
            >
              <Text size="xs" c="dimmed" mb={4}>
                Condition #{slice.points[0]?.data.x as number}
              </Text>
              {slice.points.map((point) => (
                <Group key={point.seriesId} gap={6} wrap="nowrap">
                  <Box
                    w={8}
                    h={8}
                    style={{
                      borderRadius: 2,
                      background: point.seriesColor,
                      flexShrink: 0,
                    }}
                  />
                  <Text size="xs">
                    {point.seriesId}: {Number(point.data.y).toPrecision(4)}
                  </Text>
                </Group>
              ))}
            </Box>
          )}
          useMesh
        />
      </Box>
    </Box>
  );
}
