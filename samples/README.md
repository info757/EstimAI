# EstimAI Sample Gallery

This directory contains sample PDF files for testing and demonstration purposes.

## Sample Files

### 1. Utility Construction Plans (280-utility-construction-plans.pdf)
- **Description**: Comprehensive utility construction plans with storm, sanitary, and water systems
- **Features**: 
  - Storm drainage network with inlets and pipes
  - Sanitary sewer system with manholes
  - Water distribution system with hydrants
  - Detailed pipe specifications and depths
  - Sitework elements (curb, sidewalk, silt fence)
- **Use Case**: Full-scale takeoff demonstration
- **Expected Results**: 
  - 15-20 pipes across all disciplines
  - Depth analysis with multiple buckets
  - QA flags for cover violations and deep excavation
  - Complete sitework quantities

### 2. Simple Site Plan (sample.pdf)
- **Description**: Basic site plan with minimal utility infrastructure
- **Features**:
  - Simple storm drainage
  - Basic sanitary connection
  - Minimal water system
  - Basic sitework elements
- **Use Case**: Quick demo and testing
- **Expected Results**:
  - 5-10 pipes total
  - Shallow depth analysis
  - Minimal QA flags
  - Basic sitework quantities

### 3. Complex Multi-Phase Development (complex-development.pdf)
- **Description**: Large-scale development with multiple phases and complex utility networks
- **Features**:
  - Multiple storm drainage systems
  - Extensive sanitary network
  - Water distribution with multiple loops
  - Complex sitework and earthwork
  - Multiple depth ranges and materials
- **Use Case**: Stress testing and performance demonstration
- **Expected Results**:
  - 50+ pipes across all disciplines
  - Complex depth analysis
  - Multiple QA flags
  - Extensive sitework and earthwork quantities

## Usage

### Via API
```bash
# Upload and process a sample file
curl -X POST "http://localhost:8000/api/v1/agent/takeoff" \
  -F "session_id=demo_$(date +%s)" \
  -F "upload_file=@samples/280-utility-construction-plans.pdf"
```

### Via Frontend
1. Navigate to the Review page
2. Click "Choose PDF File"
3. Select a sample file from this directory
4. Review the generated takeoff results

## Expected Performance

| Sample File | Processing Time | Pipe Count | QA Flags | PDF Size |
|-------------|----------------|------------|----------|----------|
| sample.pdf | 30-60s | 5-10 | 0-2 | <1MB |
| 280-utility-construction-plans.pdf | 60-120s | 15-20 | 3-5 | <1MB |
| complex-development.pdf | 120-300s | 50+ | 10+ | <1MB |

## Troubleshooting

### Common Issues
1. **Slow Processing**: Complex PDFs may take longer to process
2. **QA Flags**: Some samples intentionally include QA issues for demonstration
3. **Depth Analysis**: Results depend on PDF quality and scale information

### Performance Tips
1. Use smaller files for quick demos
2. Check PDF quality before processing
3. Ensure scale information is present
4. Monitor processing time for large files

## File Sources

- **280-utility-construction-plans.pdf**: Real construction plans (anonymized)
- **sample.pdf**: Simplified test case
- **complex-development.pdf**: Generated test case with complex scenarios
