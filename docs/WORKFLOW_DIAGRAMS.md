# EstimAI Workflow Diagrams

## Takeoff Workflow

### Complete Takeoff Pipeline

```mermaid
flowchart TD
    Start([User Uploads PDF]) --> Upload[/Upload File/]
    Upload --> SessionCheck{Session ID<br/>Provided?}
    
    SessionCheck -->|Yes| CheckCache[Check Session Cache]
    SessionCheck -->|No| GenSession[Generate Session ID]
    
    CheckCache --> CacheHit{Cache Hit?}
    CacheHit -->|Yes| ReturnCached[Return Cached Result]
    CacheHit -->|No| GenSession
    
    GenSession --> SaveFile[Save PDF to /files]
    SaveFile --> DetectPipeline{Pipeline<br/>Selection}
    
    DetectPipeline -->|ESTIMAI_USE_VISION=1| VisionPipeline[Vision LLM Pipeline]
    DetectPipeline -->|APR_USE_APRYSE=1| AprysePipeline[Apryse + LLM Pipeline]
    
    %% Vision Pipeline
    VisionPipeline --> VisionConvert[Convert PDF to Images]
    VisionConvert --> VisionBatch[Batch Pages<br/>Max 10 pages]
    VisionBatch --> VisionLLM[GPT-4o Vision<br/>Direct Interpretation]
    VisionLLM --> VisionParse[Parse Pipe Data<br/>Material, Dia, Length, Elevations]
    VisionParse --> MergeResults
    
    %% Apryse Pipeline
    AprysePipeline --> OpenDoc[Open PDF with PDFNet]
    OpenDoc --> ExtractScale[Extract Scale Transform<br/>feet_per_point]
    ExtractScale --> ExtractText[Extract Text Runs<br/>PyMuPDF or PDFNet]
    ExtractText --> BuildTextIndex[Build Spatial Text Index]
    BuildTextIndex --> ExtractPolylines[Extract Stroked Polylines<br/>Vector Geometry]
    ExtractPolylines --> ExtractLegend[Extract Legend Tokens]
    
    ExtractLegend --> ClassifyStorm[Classify Storm Network]
    ExtractLegend --> ClassifySanitary[Classify Sanitary Network]
    ExtractLegend --> ClassifyWater[Classify Water Network]
    
    ClassifyStorm --> StormLLM[LLM Classifier<br/>with Nearby Text]
    ClassifySanitary --> SanitaryLLM[LLM Classifier<br/>with Nearby Text]
    ClassifyWater --> WaterLLM[LLM Classifier<br/>with Nearby Text]
    
    StormLLM --> StormElevations[Extract Elevations<br/>Regex + LLM Fallback]
    SanitaryLLM --> SanitaryElevations[Extract Elevations<br/>Regex + LLM Fallback]
    WaterLLM --> WaterElevations[Extract Elevations<br/>Regex + LLM Fallback]
    
    StormElevations --> StormDepth[Calculate Depths<br/>GL - IE]
    SanitaryElevations --> SanitaryDepth[Calculate Depths<br/>GL - IE]
    WaterElevations --> WaterDepth[Calculate Depths<br/>GL - IE]
    
    StormDepth --> StormQA[Generate QA Flags<br/>Cover, Slope, etc.]
    SanitaryDepth --> SanitaryQA[Generate QA Flags<br/>Cover, Slope, etc.]
    WaterDepth --> WaterQA[Generate QA Flags<br/>Cover, Slope, etc.]
    
    StormQA --> MergeResults
    SanitaryQA --> MergeResults
    WaterQA --> MergeResults
    
    MergeResults[Merge All Networks] --> CollectUnknowns[Collect Unknown Pipes<br/>for HITL]
    CollectUnknowns --> BuildSummary[Build Summary<br/>Total Pipes, LF, QA Flags]
    
    BuildSummary --> SaveArtifacts[Save Artifacts<br/>/artifacts/session_id/]
    SaveArtifacts --> CacheResult[Cache Result<br/>by Session ID]
    CacheResult --> ReturnResult[/Return Agent Response/]
    
    ReturnCached --> End([Display Results])
    ReturnResult --> End
    
    style VisionPipeline fill:#e1f5ff
    style AprysePipeline fill:#fff4e1
    style ReturnResult fill:#d4edda
    style ReturnCached fill:#d4edda
```

### LLM Classification Detail (Apryse Pipeline)

```mermaid
flowchart TD
    Start([Polyline Candidates]) --> BuildContext[Build Context Bundle]
    
    BuildContext --> AddGeometry[Add Geometry<br/>vertices, bbox, length]
    AddGeometry --> AddNearbyText[Add Nearby Text<br/>from Spatial Index]
    AddNearbyText --> AddLegend[Add Legend Tokens<br/>from Page]
    AddLegend --> AddPageText[Add Full Page Text<br/>for LLM to read legend]
    
    AddPageText --> Canonicalize[Canonicalize Input<br/>Stable IDs, Sort, Quantize]
    Canonicalize --> ContentHash[Compute Content Hash<br/>SHA256]
    
    ContentHash --> CheckCache{Cache Hit?}
    CheckCache -->|Yes| LoadCache[Load Cached Response]
    CheckCache -->|No| CheckTokens{Token Budget<br/>< 120k?}
    
    CheckTokens -->|Yes| CallLLM[Call LLM<br/>temperature=0, seed=42]
    CheckTokens -->|No| SpatialTile[Spatial Tiling<br/>500ft chunks, 100ft overlap]
    
    SpatialTile --> CallLLMTiles[Call LLM per Tile<br/>temperature=0, seed=42]
    CallLLMTiles --> MergeTiles[Merge Tile Results]
    MergeTiles --> ValidateResult
    
    CallLLM --> ValidateResult[Validate Result<br/>Sanity Checks]
    
    ValidateResult --> SanityCheck{Improbable<br/>Result?}
    SanityCheck -->|Yes, 0 classified<br/>with good context| Retry[Retry Once<br/>Same Hash, Same Seed]
    SanityCheck -->|No| ParseResponse[Parse LLM Response<br/>Extract Classifications]
    
    Retry --> RetryCheck{Still<br/>Improbable?}
    RetryCheck -->|Yes| AddQAFlag[Add QA Flag<br/>IMPROBABLE_ZERO]
    RetryCheck -->|No| ParseResponse
    
    AddQAFlag --> ParseResponse
    ParseResponse --> ApplyRules[Apply Discipline Rules<br/>Fallback for Unknowns]
    
    ApplyRules --> WriteCache[Write to Cache<br/>/runs/session_id/]
    LoadCache --> End
    WriteCache --> End([Return Classifications])
    
    style CallLLM fill:#fff4e1
    style LoadCache fill:#d4edda
    style AddQAFlag fill:#f8d7da
```

## Evaluation Workflows

### Production Evaluation (No Ground Truth)

```mermaid
flowchart TD
    Start([Takeoff Complete]) --> ExtractText[Extract PDF Text<br/>for Faithfulness Check]
    
    ExtractText --> EvalRequest[POST /v1/evaluate/production]
    EvalRequest --> ConsistencyChecks[Run Consistency Checks]
    
    ConsistencyChecks --> CheckElevations[Check: Elevations Flow Downhill?]
    ConsistencyChecks --> CheckDepths[Check: Depths Reasonable?<br/>1-50 ft]
    ConsistencyChecks --> CheckLengths[Check: Lengths Reasonable?<br/>5-5000 ft]
    ConsistencyChecks --> CheckMaterials[Check: Materials Valid?<br/>PVC, DI, RCP, etc.]
    ConsistencyChecks --> CheckDiameters[Check: Diameters Reasonable?<br/>4-120 in]
    
    CheckElevations --> ScoreConsistency[Score Each Check<br/>1.0 = Pass, 0.5 = Warn, 0.0 = Fail]
    CheckDepths --> ScoreConsistency
    CheckLengths --> ScoreConsistency
    CheckMaterials --> ScoreConsistency
    CheckDiameters --> ScoreConsistency
    
    ScoreConsistency --> QualityMetrics[Calculate Quality Metrics]
    
    QualityMetrics --> Completeness[Completeness<br/>% with all attributes]
    QualityMetrics --> ElevationCoverage[Elevation Coverage<br/>% with elevation data]
    QualityMetrics --> Faithfulness[Faithfulness<br/>% values in PDF text]
    QualityMetrics --> MaterialCoverage[Material Coverage<br/>% with material]
    QualityMetrics --> DiameterCoverage[Diameter Coverage<br/>% with diameter]
    
    Completeness --> CalcConfidence[Calculate Overall Confidence<br/>quality*0.6 + consistency*0.4]
    ElevationCoverage --> CalcConfidence
    Faithfulness --> CalcConfidence
    MaterialCoverage --> CalcConfidence
    DiameterCoverage --> CalcConfidence
    
    CalcConfidence --> ConfidenceScore{Confidence<br/>Score}
    
    ConfidenceScore -->|≥ 0.85| HighConf[🟢 High Confidence<br/>Ready for Use]
    ConfidenceScore -->|0.70-0.85| MediumConf[🟡 Acceptable<br/>Spot Check Recommended]
    ConfidenceScore -->|0.50-0.70| LowConf[🟠 Low Confidence<br/>Human Review Required]
    ConfidenceScore -->|< 0.50| VeryLowConf[🔴 Very Low<br/>Manual Takeoff Recommended]
    
    HighConf --> AutoCommit[Auto-Commit to Database]
    MediumConf --> CommitWithWarning[Commit with Warning<br/>Flag for Spot Check]
    LowConf --> HITLQueue[Queue for HITL Review]
    VeryLowConf --> HITLQueue
    
    AutoCommit --> End([Workflow Complete])
    CommitWithWarning --> End
    HITLQueue --> End
    
    style HighConf fill:#d4edda
    style MediumConf fill:#fff3cd
    style LowConf fill:#f8d7da
    style VeryLowConf fill:#f8d7da
```

### Benchmark Evaluation (With Ground Truth)

```mermaid
flowchart TD
    Start([Generate Synthetic PDF]) --> DefineGroundTruth[Define Ground Truth<br/>Exact Counts, Lengths, Elevations]
    
    DefineGroundTruth --> GeneratePDF[Generate Vector PDF<br/>ReportLab with Plan + Profile]
    GeneratePDF --> RunTakeoff[Run Takeoff Agent<br/>Same as Production]
    
    RunTakeoff --> EvalRequest[POST /v1/evaluate/benchmark]
    
    EvalRequest --> CountMetric[Pipe Count Accuracy<br/>predicted vs. actual]
    EvalRequest --> ElevationMetric[Elevation Accuracy<br/>IE_in, IE_out ±5ft]
    EvalRequest --> LengthMetric[Length Accuracy<br/>LF ±20%]
    EvalRequest --> MaterialMetric[Material Accuracy<br/>Fuzzy Match]
    
    CountMetric --> CountScore{Count<br/>Error}
    CountScore -->|0%| Count100[100% Accuracy]
    CountScore -->|≤50%| CountPartial[Partial Accuracy<br/>1.0 - error/0.5]
    CountScore -->|>50%| Count0[0% Accuracy]
    
    ElevationMetric --> ElevScore{Elevation<br/>Error}
    ElevScore -->|≤1 ft| Elev100[100% Accuracy]
    ElevScore -->|1-5 ft| ElevPartial[Partial Accuracy<br/>1.0 - error/5.0]
    ElevScore -->|>5 ft| Elev0[0% Accuracy]
    
    LengthMetric --> LengthScore{Length<br/>Error}
    LengthScore -->|≤5%| Length100[100% Accuracy]
    LengthScore -->|5-20%| LengthPartial[Partial Accuracy<br/>1.0 - error/0.20]
    LengthScore -->|>20%| Length0[0% Accuracy]
    
    MaterialMetric --> MatScore{Material<br/>Match}
    MatScore -->|Exact| Mat100[100% Accuracy]
    MatScore -->|Partial| Mat50[50% Accuracy]
    MatScore -->|No Match| Mat0[0% Accuracy]
    
    Count100 --> CalcOverall[Calculate Overall Accuracy<br/>Average All Metrics]
    CountPartial --> CalcOverall
    Count0 --> CalcOverall
    Elev100 --> CalcOverall
    ElevPartial --> CalcOverall
    Elev0 --> CalcOverall
    Length100 --> CalcOverall
    LengthPartial --> CalcOverall
    Length0 --> CalcOverall
    Mat100 --> CalcOverall
    Mat50 --> CalcOverall
    Mat0 --> CalcOverall
    
    CalcOverall --> LogLangSmith[Log to LangSmith<br/>Track Over Time]
    LogLangSmith --> OverallScore{Overall<br/>Accuracy}
    
    OverallScore -->|≥ 95%| Excellent[✅ Excellent<br/>Production Ready]
    OverallScore -->|85-95%| Good[✅ Good<br/>Minor Tuning]
    OverallScore -->|70-85%| Fair[⚠️ Fair<br/>Needs Improvement]
    OverallScore -->|< 70%| Poor[❌ Poor<br/>Major Issues]
    
    Excellent --> UpdateBaseline[Update Baseline<br/>Merge PR]
    Good --> UpdateBaseline
    Fair --> Investigate[Investigate Regression<br/>Fix or Justify]
    Poor --> Investigate
    
    UpdateBaseline --> End([Benchmark Complete])
    Investigate --> End
    
    style Excellent fill:#d4edda
    style Good fill:#d4edda
    style Fair fill:#fff3cd
    style Poor fill:#f8d7da
```

### Combined Evaluation Strategy

```mermaid
flowchart TD
    Start([PDF Received]) --> PDFType{PDF Type}
    
    PDFType -->|Synthetic<br/>Development| BenchmarkPath[Benchmark Evaluation Path]
    PDFType -->|Real<br/>Production| ProductionPath[Production Evaluation Path]
    
    %% Benchmark Path
    BenchmarkPath --> KnownGT[Known Ground Truth<br/>Available]
    KnownGT --> RunBenchmark[Run Benchmark Evaluation]
    RunBenchmark --> CompareExact[Compare Exact Values<br/>Count, Length, Elevation]
    CompareExact --> BenchScore{Accuracy<br/>Score}
    
    BenchScore -->|≥ 95%| BenchPass[✅ Pass<br/>Merge to Main]
    BenchScore -->|< 95%| BenchFail[❌ Fail<br/>Investigate Regression]
    
    BenchPass --> CIComplete[CI Complete]
    BenchFail --> FixIssue[Fix Issue<br/>Re-run Tests]
    FixIssue --> RunBenchmark
    
    %% Production Path
    ProductionPath --> NoGT[No Ground Truth<br/>Available]
    NoGT --> RunProduction[Run Production Evaluation]
    RunProduction --> CheckConsistency[Check Internal Consistency<br/>+ Faithfulness]
    CheckConsistency --> ProdScore{Confidence<br/>Score}
    
    ProdScore -->|≥ 0.85| HighConf[🟢 High Confidence]
    ProdScore -->|0.70-0.85| MedConf[🟡 Medium Confidence]
    ProdScore -->|< 0.70| LowConf[🔴 Low Confidence]
    
    HighConf --> AutoApprove[Auto-Approve<br/>Commit to Database]
    MedConf --> SpotCheck[Flag for Spot Check<br/>Commit with Warning]
    LowConf --> HITLReview[Queue for HITL Review<br/>Human Verification]
    
    AutoApprove --> CustomerDelivery[Deliver to Customer]
    SpotCheck --> CustomerDelivery
    HITLReview --> HumanReview[Human Reviews<br/>Corrects Errors]
    HumanReview --> CustomerDelivery
    
    CustomerDelivery --> TrackMetrics[Track Metrics<br/>LangSmith + Analytics]
    CIComplete --> TrackMetrics
    
    TrackMetrics --> End([Continuous Improvement])
    
    style BenchPass fill:#d4edda
    style BenchFail fill:#f8d7da
    style HighConf fill:#d4edda
    style MedConf fill:#fff3cd
    style LowConf fill:#f8d7da
```

## Determinism & Caching Flow

```mermaid
flowchart TD
    Start([LLM Classification Request]) --> BuildBundle[Build Input Bundle<br/>Geometry + Text + Legend]
    
    BuildBundle --> Canonicalize[Canonicalize Input]
    
    Canonicalize --> StableIDs[Stable IDs<br/>Hash of vertices]
    Canonicalize --> SortArrays[Sort Arrays<br/>Polylines, Labels]
    Canonicalize --> QuantizeFloats[Quantize Floats<br/>3 decimals, null for NaN]
    Canonicalize --> ExplicitUnits[Explicit Units<br/>Always include scale]
    
    StableIDs --> ComputeHash[Compute Content Hash<br/>SHA256 of normalized JSON]
    SortArrays --> ComputeHash
    QuantizeFloats --> ComputeHash
    ExplicitUnits --> ComputeHash
    
    ComputeHash --> BuildCacheKey[Build Cache Key<br/>model + prompt_v + schema_v + hash]
    
    BuildCacheKey --> CheckCache{Cache<br/>Hit?}
    
    CheckCache -->|Yes| LoadCache[Load Cached Response<br/>/runs/session_id/cache/]
    CheckCache -->|No| PrepareCall[Prepare LLM Call]
    
    PrepareCall --> SetParams[Set Deterministic Params<br/>temp=0, top_p=1, seed=42]
    SetParams --> EstimateTokens[Estimate Token Usage]
    
    EstimateTokens --> TokenCheck{Tokens<br/>< 120k?}
    
    TokenCheck -->|Yes| CallLLM[Call LLM<br/>Single Request]
    TokenCheck -->|No| SpatialTile[Spatial Tiling<br/>500ft chunks]
    
    SpatialTile --> CallLLMTiles[Call LLM per Tile<br/>Parallel Requests]
    CallLLMTiles --> MergeTiles[Merge Tile Results<br/>Deduplicate Overlaps]
    MergeTiles --> ValidateResponse
    
    CallLLM --> ValidateResponse[Validate Response<br/>Sanity Checks]
    
    ValidateResponse --> SanityCheck{Improbable<br/>Result?}
    
    SanityCheck -->|Yes| RetryOnce[Retry Once<br/>Same Cache Key]
    SanityCheck -->|No| ParseResult[Parse Result]
    
    RetryOnce --> StillBad{Still<br/>Bad?}
    StillBad -->|Yes| AddFlag[Add QA Flag<br/>IMPROBABLE_ZERO]
    StillBad -->|No| ParseResult
    
    AddFlag --> ParseResult
    ParseResult --> WriteCache[Write to Cache<br/>Request + Response + Metadata]
    
    WriteCache --> LogMetadata[Log Metadata<br/>content_hash, prompt_v, tokens]
    LoadCache --> LogMetadata
    
    LogMetadata --> ReturnResult[Return Classifications<br/>+ Cache Metadata]
    
    ReturnResult --> End([Deterministic Result])
    
    style LoadCache fill:#d4edda
    style CallLLM fill:#fff4e1
    style AddFlag fill:#f8d7da
```

## Usage Examples

### View Diagrams

These diagrams are written in Mermaid syntax and can be viewed in:

1. **GitHub** - Automatically renders in README.md and .md files
2. **VS Code** - Install "Markdown Preview Mermaid Support" extension
3. **Mermaid Live Editor** - https://mermaid.live/
4. **Documentation Sites** - MkDocs, Docusaurus, etc.

### Customize

To modify these diagrams:

1. Copy the Mermaid code block
2. Paste into https://mermaid.live/
3. Edit and preview in real-time
4. Copy updated code back to this file

### Export

From Mermaid Live Editor, you can export as:
- PNG image
- SVG vector graphic
- PDF document
- Markdown with embedded diagram

