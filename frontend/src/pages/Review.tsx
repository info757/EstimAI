/**
 * Review Page for Human-in-the-Loop Takeoff Review
 * 
 * Provides interface for reviewing and curating takeoff results
 * before committing to the database.
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Chip,
  Grid,
  Card,
  CardContent,
  CardActions
} from '@mui/material';
import {
  Upload as UploadIcon,
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import ReviewTable from '../features/review/ReviewTable';

interface PipeItem {
  id: string;
  category: string;
  subtype: string;
  name: string;
  quantity: number;
  unit: string;
  attributes: {
    csi?: string;
    unit_price?: number;
    total_price?: number;
    diameter_in?: number;
    material?: string;
    avg_depth_ft?: number;
    min_depth_ft?: number;
    max_depth_ft?: number;
    p95_depth_ft?: number;
    d_0_5?: number;
    d_5_8?: number;
    d_8_12?: number;
    d_12_plus?: number;
    trench_volume_cy?: number;
    cover_ok?: boolean;
    deep_excavation?: boolean;
    ground_source?: string;
    pipe_id?: string;
    from_id?: string;
    to_id?: string;
  };
  source_ref: {
    sheet: string;
    geom_id: string;
    hash: string;
  };
  status?: 'pending' | 'accepted' | 'rejected' | 'committed';
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`review-tabpanel-${index}`}
      aria-labelledby={`review-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const Review: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [items, setItems] = useState<PipeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>('');

  // Load items from API
  const loadItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/counts');
      if (!response.ok) {
        throw new Error('Failed to load items');
      }
      const data = await response.json();
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load items');
    } finally {
      setLoading(false);
    }
  };

  // Run agent takeoff
  const runAgentTakeoff = async (file: File) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const formData = new FormData();
      formData.append('session_id', `review_${Date.now()}`);
      formData.append('upload_file', file);
      
      const response = await fetch('/api/v1/agent/takeoff', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Agent takeoff failed');
      }
      
      const result = await response.json();
      setSessionId(result.proposed_review.session_id);
      setSuccess(`Agent processing completed. Found ${result.summary.networks.storm.pipes + result.summary.networks.sanitary.pipes + result.summary.networks.water.pipes} pipes.`);
      
      // Load the new items
      await loadItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Agent takeoff failed');
    } finally {
      setLoading(false);
    }
  };

  // Handle file upload
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      runAgentTakeoff(file);
    }
  };

  // Handle item accept
  const handleAccept = (itemId: string) => {
    setItems(prevItems =>
      prevItems.map(item =>
        item.id === itemId ? { ...item, status: 'accepted' as const } : item
      )
    );
  };

  // Handle item reject
  const handleReject = (itemId: string) => {
    setItems(prevItems =>
      prevItems.map(item =>
        item.id === itemId ? { ...item, status: 'rejected' as const } : item
      )
    );
  };

  // Handle commit
  const handleCommit = async (acceptedItems: PipeItem[]) => {
    setLoading(true);
    setError(null);
    
    try {
      // Convert items to the format expected by the review commit endpoint
      const commitData = {
        session_id: sessionId || 'review',
        sheet_ref: 'AUTO',
        payload: {
          sheet_units: 'ft',
          scale: '1" = 50\'',
          networks: {
            storm: {
              pipes: acceptedItems.filter(item => item.category.includes('storm')).map(item => ({
                id: item.attributes.pipe_id || item.id,
                from_id: item.attributes.from_id,
                to_id: item.attributes.to_id,
                length_ft: item.quantity,
                dia_in: item.attributes.diameter_in,
                mat: item.attributes.material,
                avg_depth_ft: item.attributes.avg_depth_ft,
                extra: {
                  min_depth_ft: item.attributes.min_depth_ft,
                  max_depth_ft: item.attributes.max_depth_ft,
                  p95_depth_ft: item.attributes.p95_depth_ft,
                  buckets_lf: {
                    '0-5': item.attributes.d_0_5 || 0,
                    '5-8': item.attributes.d_5_8 || 0,
                    '8-12': item.attributes.d_8_12 || 0,
                    '12+': item.attributes.d_12_plus || 0
                  },
                  trench_volume_cy: item.attributes.trench_volume_cy,
                  cover_ok: item.attributes.cover_ok,
                  deep_excavation: item.attributes.deep_excavation,
                  ground_source: item.attributes.ground_source
                }
              })),
              structures: []
            },
            sanitary: {
              pipes: acceptedItems.filter(item => item.category.includes('sanitary')).map(item => ({
                id: item.attributes.pipe_id || item.id,
                from_id: item.attributes.from_id,
                to_id: item.attributes.to_id,
                length_ft: item.quantity,
                dia_in: item.attributes.diameter_in,
                mat: item.attributes.material,
                avg_depth_ft: item.attributes.avg_depth_ft,
                extra: {
                  min_depth_ft: item.attributes.min_depth_ft,
                  max_depth_ft: item.attributes.max_depth_ft,
                  p95_depth_ft: item.attributes.p95_depth_ft,
                  buckets_lf: {
                    '0-5': item.attributes.d_0_5 || 0,
                    '5-8': item.attributes.d_5_8 || 0,
                    '8-12': item.attributes.d_8_12 || 0,
                    '12+': item.attributes.d_12_plus || 0
                  },
                  trench_volume_cy: item.attributes.trench_volume_cy,
                  cover_ok: item.attributes.cover_ok,
                  deep_excavation: item.attributes.deep_excavation,
                  ground_source: item.attributes.ground_source
                }
              })),
              manholes: []
            },
            water: {
              pipes: acceptedItems.filter(item => item.category.includes('water')).map(item => ({
                id: item.attributes.pipe_id || item.id,
                from_id: item.attributes.from_id,
                to_id: item.attributes.to_id,
                length_ft: item.quantity,
                dia_in: item.attributes.diameter_in,
                mat: item.attributes.material,
                avg_depth_ft: item.attributes.avg_depth_ft,
                extra: {
                  min_depth_ft: item.attributes.min_depth_ft,
                  max_depth_ft: item.attributes.max_depth_ft,
                  p95_depth_ft: item.attributes.p95_depth_ft,
                  buckets_lf: {
                    '0-5': item.attributes.d_0_5 || 0,
                    '5-8': item.attributes.d_5_8 || 0,
                    '8-12': item.attributes.d_8_12 || 0,
                    '12+': item.attributes.d_12_plus || 0
                  },
                  trench_volume_cy: item.attributes.trench_volume_cy,
                  cover_ok: item.attributes.cover_ok,
                  deep_excavation: item.attributes.deep_excavation,
                  ground_source: item.attributes.ground_source
                }
              })),
              hydrants: [],
              valves: []
            }
          },
          roadway: {
            curb_lf: 0,
            sidewalk_sf: 0
          },
          e_sc: {
            silt_fence_lf: 0,
            inlet_protection_ea: 0
          },
          earthwork: {
            cut_cy: null,
            fill_cy: null,
            source: 'table'
          },
          qa_flags: []
        }
      };

      const response = await fetch('/api/v1/takeoff/review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(commitData)
      });

      if (!response.ok) {
        throw new Error('Failed to commit items');
      }

      const result = await response.json();
      setSuccess(result.message || 'Items committed successfully');
      
      // Update item statuses
      setItems(prevItems =>
        prevItems.map(item =>
          acceptedItems.some(accepted => accepted.id === item.id)
            ? { ...item, status: 'committed' as const }
            : item
        )
      );
      
      // Reload items to get updated data
      await loadItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to commit items');
    } finally {
      setLoading(false);
    }
  };

  // Load items on component mount
  useEffect(() => {
    loadItems();
  }, []);

  // Filter items by status
  const pendingItems = items.filter(item => item.status === 'pending' || !item.status);
  const acceptedItems = items.filter(item => item.status === 'accepted');
  const rejectedItems = items.filter(item => item.status === 'rejected');
  const committedItems = items.filter(item => item.status === 'committed');

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Takeoff Review
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Review and curate takeoff results before committing to the database.
      </Typography>

      {/* File Upload */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Upload PDF for Analysis
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="contained"
            component="label"
            startIcon={<UploadIcon />}
            disabled={loading}
          >
            Choose PDF File
            <input
              type="file"
              hidden
              accept=".pdf"
              onChange={handleFileUpload}
            />
          </Button>
          {loading && <CircularProgress size={24} />}
        </Box>
      </Paper>

      {/* Status Messages */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="primary">
                {pendingItems.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pending Review
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="success.main">
                {acceptedItems.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Accepted
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="error.main">
                {rejectedItems.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Rejected
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="info.main">
                {committedItems.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Committed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Review Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
            <Tab label={`All Items (${items.length})`} />
            <Tab label={`Pending (${pendingItems.length})`} />
            <Tab label={`Accepted (${acceptedItems.length})`} />
            <Tab label={`Rejected (${rejectedItems.length})`} />
            <Tab label={`Committed (${committedItems.length})`} />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <ReviewTable
            items={items}
            onAccept={handleAccept}
            onReject={handleReject}
            onCommit={handleCommit}
            loading={loading}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <ReviewTable
            items={pendingItems}
            onAccept={handleAccept}
            onReject={handleReject}
            onCommit={handleCommit}
            loading={loading}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <ReviewTable
            items={acceptedItems}
            onAccept={handleAccept}
            onReject={handleReject}
            onCommit={handleCommit}
            loading={loading}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <ReviewTable
            items={rejectedItems}
            onAccept={handleAccept}
            onReject={handleReject}
            onCommit={handleCommit}
            loading={loading}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <ReviewTable
            items={committedItems}
            onAccept={handleAccept}
            onReject={handleReject}
            onCommit={handleCommit}
            loading={loading}
          />
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default Review;