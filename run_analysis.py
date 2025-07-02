import logging
from pathlib import Path
import sys

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_learner.cli.code_analyzer_cli import CodeAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    project_path = Path("/home/flyingcloud/work/project/code-repo-learner/reference_code_repo")
    project_id = "auto_086e94dd"
    
    logger.info(f"Starting analysis for project: {project_path}")
    logger.info(f"Using Project ID: {project_id}")
    
    try:
        # Initialize the analyzer directly
        analyzer = CodeAnalyzer(
            project_path=project_path,
            project_id=project_id,
            threads=8  # Use more threads for faster analysis
        )
        
        # Run the analysis
        stats = analyzer.analyze(generate_embeddings=False) # Skip embeddings for now to speed up
        
        logger.info("Analysis finished successfully.")
        logger.info(f"Stats: {stats}")
        
    except Exception as e:
        logger.error(f"An error occurred during analysis: {e}", exc_info=True)

if __name__ == "__main__":
    main() 