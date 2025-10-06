/**
 * Review Table Component for Human-in-the-Loop Takeoff Review
 * 
 * Displays proposed vs committed items with accept/reject actions,
 * QA badges, and batch commit functionality.
 */
import React, { useState, useEffect } from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  Chip, 
  Button, 
  Box, 
  Typography, 
  Alert,
  CircularProgress,
  Checkbox,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import { 
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Warning as WarningIcon,
  Info as InfoIcon
} from '@mui/icons-material';

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

interface QABadge {
  code: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

interface ReviewTableProps {
  items: PipeItem[];
  onAccept: (itemId: string) => void;
  onReject: (itemId: string) => void;
  onCommit: (acceptedItems: PipeItem[]) => Promise<void>;
  loading?: boolean;
}

const ReviewTable: React.FC<ReviewTableProps> = ({
  items,
  onAccept,
  onReject,
  onCommit,
  loading = false
}) => {
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [commitLoading, setCommitLoading] = useState(false);
  const [commitMessage, setCommitMessage] = useState('');

  // Filter items by status
  const pendingItems = items.filter(item => item.status === 'pending' || !item.status);
  const acceptedItems = items.filter(item => item.status === 'accepted');
  const rejectedItems = items.filter(item => item.status === 'rejected');
  const committedItems = items.filter(item => item.status === 'committed');

  // Get QA badges for an item
  const getQABadges = (item: PipeItem): QABadge[] => {
    const badges: QABadge[] = [];
    const attrs = item.attributes;

    if (attrs.cover_ok === false) {
      badges.push({
        code: 'COVER_LOW',
        message: 'Pipe cover below minimum requirement',
        severity: 'error'
      });
    }

    if (attrs.deep_excavation === true) {
      badges.push({
        code: 'DEEP_EXCAVATION',
        message: 'Deep excavation required (>12ft)',
        severity: 'warning'
      });
    }

    if (attrs.ground_source === 'constant') {
      badges.push({
        code: 'GROUND_FALLBACK',
        message: 'Using constant ground elevation (no survey data)',
        severity: 'info'
      });
    }

    return badges;
  };

  // Get status chip
  const getStatusChip = (status: string) => {
    switch (status) {
      case 'accepted':
        return <Chip icon={<CheckCircleIcon />} label="Accepted" color="success" size="small" />;
      case 'rejected':
        return <Chip icon={<CancelIcon />} label="Rejected" color="error" size="small" />;
      case 'committed':
        return <Chip icon={<CheckCircleIcon />} label="Committed" color="primary" size="small" />;
      default:
        return <Chip label="Pending" color="default" size="small" />;
    }
  };

  // Get severity icon
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <CancelIcon color="error" fontSize="small" />;
      case 'warning':
        return <WarningIcon color="warning" fontSize="small" />;
      case 'info':
        return <InfoIcon color="info" fontSize="small" />;
      default:
        return <InfoIcon fontSize="small" />;
    }
  };

  // Handle item selection
  const handleSelectItem = (itemId: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  // Handle select all
  const handleSelectAll = () => {
    if (selectedItems.size === pendingItems.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(pendingItems.map(item => item.id)));
    }
  };

  // Handle batch accept
  const handleBatchAccept = () => {
    selectedItems.forEach(itemId => {
      onAccept(itemId);
    });
    setSelectedItems(new Set());
  };

  // Handle batch reject
  const handleBatchReject = () => {
    selectedItems.forEach(itemId => {
      onReject(itemId);
    });
    setSelectedItems(new Set());
  };

  // Handle commit
  const handleCommit = async () => {
    const itemsToCommit = acceptedItems.filter(item => !committedItems.some(committed => committed.id === item.id));
    if (itemsToCommit.length === 0) {
      setCommitMessage('No accepted items to commit');
      return;
    }

    setCommitLoading(true);
    try {
      await onCommit(itemsToCommit);
      setCommitMessage(`Successfully committed ${itemsToCommit.length} items`);
    } catch (error) {
      setCommitMessage(`Error committing items: ${error}`);
    } finally {
      setCommitLoading(false);
    }
  };

  // Render item details
  const renderItemDetails = (item: PipeItem) => {
    const attrs = item.attributes;
    const qaBadges = getQABadges(item);

    return (
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle2">
            {item.category} - {item.name} ({item.quantity} {item.unit})
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Basic Info */}
            <Box>
              <Typography variant="subtitle2" gutterBottom>Basic Information</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 1 }}>
                <Typography variant="body2">Pipe ID: {attrs.pipe_id || 'N/A'}</Typography>
                <Typography variant="body2">Material: {attrs.material || 'N/A'}</Typography>
                <Typography variant="body2">Diameter: {attrs.diameter_in || 'N/A'}"</Typography>
                <Typography variant="body2">Length: {item.quantity} {item.unit}</Typography>
                <Typography variant="body2">CSI: {attrs.csi || 'N/A'}</Typography>
                <Typography variant="body2">Ground Source: {attrs.ground_source || 'N/A'}</Typography>
              </Box>
            </Box>

            {/* Depth Information */}
            <Box>
              <Typography variant="subtitle2" gutterBottom>Depth Analysis</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1 }}>
                <Typography variant="body2">Min Depth: {attrs.min_depth_ft?.toFixed(1) || 'N/A'} ft</Typography>
                <Typography variant="body2">Avg Depth: {attrs.avg_depth_ft?.toFixed(1) || 'N/A'} ft</Typography>
                <Typography variant="body2">Max Depth: {attrs.max_depth_ft?.toFixed(1) || 'N/A'} ft</Typography>
                <Typography variant="body2">P95 Depth: {attrs.p95_depth_ft?.toFixed(1) || 'N/A'} ft</Typography>
              </Box>
              
              {/* Depth Buckets */}
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" gutterBottom>Depth Buckets (LF):</Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {attrs.d_0_5 && attrs.d_0_5 > 0 && (
                    <Chip label={`0-5ft: ${attrs.d_0_5.toFixed(1)}`} size="small" color="primary" />
                  )}
                  {attrs.d_5_8 && attrs.d_5_8 > 0 && (
                    <Chip label={`5-8ft: ${attrs.d_5_8.toFixed(1)}`} size="small" color="secondary" />
                  )}
                  {attrs.d_8_12 && attrs.d_8_12 > 0 && (
                    <Chip label={`8-12ft: ${attrs.d_8_12.toFixed(1)}`} size="small" color="warning" />
                  )}
                  {attrs.d_12_plus && attrs.d_12_plus > 0 && (
                    <Chip label={`12+ft: ${attrs.d_12_plus.toFixed(1)}`} size="small" color="error" />
                  )}
                </Box>
              </Box>

              {/* Trench Volume */}
              {attrs.trench_volume_cy && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    Trench Volume: {attrs.trench_volume_cy.toFixed(1)} CY
                  </Typography>
                </Box>
              )}
            </Box>

            {/* QA Badges */}
            {qaBadges.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Quality Assurance</Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {qaBadges.map((badge, index) => (
                    <Chip
                      key={index}
                      icon={getSeverityIcon(badge.severity)}
                      label={badge.message}
                      color={badge.severity === 'error' ? 'error' : badge.severity === 'warning' ? 'warning' : 'info'}
                      size="small"
                    />
                  ))}
                </Box>
              </Box>
            )}

            {/* Pricing */}
            {(attrs.unit_price || attrs.total_price) && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Pricing</Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  {attrs.unit_price && (
                    <Typography variant="body2">Unit Price: ${attrs.unit_price.toFixed(2)}</Typography>
                  )}
                  {attrs.total_price && (
                    <Typography variant="body2">Total: ${attrs.total_price.toFixed(2)}</Typography>
                  )}
                </Box>
              </Box>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      {/* Summary */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>Review Summary</Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip label={`Pending: ${pendingItems.length}`} color="default" />
          <Chip label={`Accepted: ${acceptedItems.length}`} color="success" />
          <Chip label={`Rejected: ${rejectedItems.length}`} color="error" />
          <Chip label={`Committed: ${committedItems.length}`} color="primary" />
        </Box>
      </Box>

      {/* Commit Message */}
      {commitMessage && (
        <Alert severity={commitMessage.includes('Error') ? 'error' : 'success'} sx={{ mb: 2 }}>
          {commitMessage}
        </Alert>
      )}

      {/* Batch Actions */}
      {pendingItems.length > 0 && (
        <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>Batch Actions</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={selectedItems.size === pendingItems.length && pendingItems.length > 0}
                  indeterminate={selectedItems.size > 0 && selectedItems.size < pendingItems.length}
                  onChange={handleSelectAll}
                />
              }
              label="Select All"
            />
            <Button
              variant="outlined"
              color="success"
              onClick={handleBatchAccept}
              disabled={selectedItems.size === 0}
            >
              Accept Selected ({selectedItems.size})
            </Button>
            <Button
              variant="outlined"
              color="error"
              onClick={handleBatchReject}
              disabled={selectedItems.size === 0}
            >
              Reject Selected ({selectedItems.size})
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleCommit}
              disabled={acceptedItems.length === 0 || commitLoading}
              startIcon={commitLoading ? <CircularProgress size={20} /> : <CheckCircleIcon />}
            >
              Commit Accepted ({acceptedItems.length})
            </Button>
          </Box>
        </Box>
      )}

      {/* Items Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Select</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Details</TableCell>
              <TableCell>Quantity</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>QA</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell>
                  {item.status === 'pending' || !item.status ? (
                    <Checkbox
                      checked={selectedItems.has(item.id)}
                      onChange={() => handleSelectItem(item.id)}
                    />
                  ) : null}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {item.category}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {item.subtype}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{item.name}</Typography>
                  {item.attributes.pipe_id && (
                    <Typography variant="caption" color="text.secondary">
                      ID: {item.attributes.pipe_id}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {item.quantity} {item.unit}
                  </Typography>
                </TableCell>
                <TableCell>
                  {getStatusChip(item.status || 'pending')}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {getQABadges(item).map((badge, index) => (
                      <Chip
                        key={index}
                        icon={getSeverityIcon(badge.severity)}
                        label={badge.code}
                        color={badge.severity === 'error' ? 'error' : badge.severity === 'warning' ? 'warning' : 'info'}
                        size="small"
                      />
                    ))}
                  </Box>
                </TableCell>
                <TableCell>
                  {item.status === 'pending' || !item.status ? (
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        color="success"
                        onClick={() => onAccept(item.id)}
                        startIcon={<CheckCircleIcon />}
                      >
                        Accept
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => onReject(item.id)}
                        startIcon={<CancelIcon />}
                      >
                        Reject
                      </Button>
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      {item.status === 'committed' ? 'Committed' : item.status === 'accepted' ? 'Accepted' : 'Rejected'}
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Item Details */}
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>Item Details</Typography>
        {items.map((item) => (
          <Box key={`details-${item.id}`} sx={{ mb: 2 }}>
            {renderItemDetails(item)}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default ReviewTable;
