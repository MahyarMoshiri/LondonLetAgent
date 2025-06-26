import asyncio
import click
from typing import List, Optional

# Import UserCriteria from the new models.py
from .models import UserCriteria 
# Import the main agent runner from main.py
from .main import run_agent_with_criteria

# Configure logging
from .logging_module import setup_logging, get_logger

logger = get_logger("InputModule")

@click.command()
@click.option("--location", required=True, help="Target location for property search (e.g., 'North West London', 'NW1', etc.).")
@click.option("--property-type", help="Type of property (e.g., flat, house, studio).")
@click.option("--price-min", type=int, help="Minimum price.")
@click.option("--price-max", type=int, help="Maximum price.")
@click.option("--bedrooms-min", type=int, help="Minimum number of bedrooms.")
@click.option("--keywords", multiple=True, help="Specific keywords to search for (can be used multiple times).")
@click.option("--private-only", is_flag=True, help="Find listings from private landlords only.")
@click.option("--exclude-agents", is_flag=True, default=True, show_default=True, help="Exclude listings from agents.")
def get_user_criteria_and_run_agent(location: str, property_type: Optional[str], 
                                   price_min: Optional[int], price_max: Optional[int], 
                                   bedrooms_min: Optional[int], keywords: Optional[List[str]], 
                                   private_only: bool, exclude_agents: bool):
    """
    Collects user search criteria via CLI and runs the Gumtree-only property canvassing agent.
    
    For broad area searches like 'North West London', the agent will automatically expand
    to search all relevant postcodes (e.g., NW1-NW11) for more comprehensive results.
    """
    if price_min is not None and price_max is not None and price_min > price_max:
        logger.error("Error: Minimum price cannot be greater than maximum price.")
        click.echo("Error: Minimum price cannot be greater than maximum price.", err=True)
        return

    criteria = UserCriteria(
        location=location,
        property_type=property_type,
        price_min=price_min,
        price_max=price_max,
        bedrooms_min=bedrooms_min,
        keywords=list(keywords) if keywords else [],
        private_only=private_only,
        exclude_agents=exclude_agents
    )

    logger.info(f"User criteria collected: {criteria.model_dump()}")
    click.echo(f"Starting Gumtree property search with criteria: {criteria.model_dump()}")
    click.echo(f"For broad areas like '{location}', the agent will automatically search all relevant postcodes.")
    
    asyncio.run(run_agent_with_criteria(criteria))
    click.echo("Gumtree property search agent has finished.")

if __name__ == "__main__":
    # One-time setup of logging if this script is the entry point
    setup_logging() 
    logger.info("Gumtree-only input module run directly.")
    get_user_criteria_and_run_agent()
