"""Example: How to use Structured Memory in agents.

This example shows how SCOUT agent would use the new memory system
to maintain context between runs.
"""

# Example 1: SCOUT Agent using working memory
async def example_scout_with_memory():
    """Example of how SCOUT would use structured memory."""
    
    # At the start of run - check what we were working on
    working = await self.get_working_memory()
    
    if working.status == "in_progress":
        # We have an ongoing task - continue from where we left off
        print(f"Continuing: {working.title}")
        print(f"Previous progress: {working.progress_percent}%")
        print(f"Notes from last run: {working.notes}")
        
        # Only analyze new data since last run
        # Instead of re-analyzing everything
        new_data = await self._get_new_data_since(working.last_updated)
        
    else:
        # Start fresh
        await self.update_working_memory(
            title="Market Opportunity Scan",
            description="Scanning BTC, ETH, XAU for opportunities",
            status="in_progress",
            progress_percent=0,
            next_steps=[
                "Analyze BTC sentiment trends",
                "Check ETH volume spikes",
                "Monitor XAU price movements",
                "Compile opportunity report"
            ]
        )
    
    # Do the work...
    opportunities = await self._analyze_markets()
    
    # Update progress
    await self.update_working_memory(
        title="Market Opportunity Scan",
        description=f"Found {len(opportunities)} opportunities",
        status="in_progress",
        progress_percent=75,
        next_steps=[
            "Validate high-priority opportunities",
            "Publish findings to Pub/Sub",
            "Update trend database"
        ],
        notes=f"Detected major shift in BTC sentiment ({opportunities[0]['sentiment_change']:.2%})"
    )
    
    # Log the activity
    await self.log_activity(
        action="Opportunity Detection",
        details=f"Analyzed {len(opportunities)} assets, detected {len([o for o in opportunities if o['opportunity_score'] > 7])} high-value opportunities",
        result=f"Top opportunity: BTC with score {opportunities[0]['opportunity_score']:.1f}"
    )
    
    # Save important learnings
    if opportunities[0]['opportunity_score'] > 8:
        await self.remember(
            category="market_patterns",
            key="btc_sentiment_surge",
            value=f"BTC sentiment surged {opportunities[0]['sentiment_change']:.2%} in 24h. Previous similar surge led to 15% price increase over 3 days.",
            importance="high"
        )


# Example 2: ORACLE Agent using long-term memory
async def example_oracle_with_memory():
    """Example of how ORACLE would use memory for validation."""
    
    # Check if we already validated this opportunity
    long_term = await self.memory.get_long_term_memory(category="validations")
    
    # Get the opportunity to validate
    opportunity = await self._get_opportunity_from_scout()
    
    # Check if we validated similar opportunity before
    for mem in long_term:
        if opportunity['asset'] in mem.get('value', ''):
            print(f"Found previous validation for {opportunity['asset']}")
            print(f"Previous result: {mem['value']}")
            # Use cached validation if recent enough
            
    # Perform validation
    validation_result = await self._validate_opportunity(opportunity)
    
    # Save validation to memory
    await self.remember(
        category="validations",
        key=f"validation_{opportunity['asset']}_{datetime.now().strftime('%Y%m%d')}",
        value=f"Validated {opportunity['asset']} opportunity: p-value={validation_result['p_value']:.3f}, confidence={validation_result['confidence']:.1%}",
        importance="high" if validation_result['confidence'] > 0.8 else "medium"
    )


# Example 3: SETH Agent using memory for content continuity
async def example_seth_with_memory():
    """Example of how SETH would use memory for content creation."""
    
    # Check what we were writing
    working = await self.get_working_memory()
    
    if working.title and "blog" in working.title.lower():
        # Continue working on blog post
        print(f"Continuing blog post: {working.title}")
        print(f"Progress: {working.progress_percent}%")
        
        # Load previous work
        previous_drafts = await self.memory.get_daily_notes()
        
        # Continue from where we left off
        blog_post = await self._continue_blog_post(
            topic=working.title,
            previous_progress=working.notes,
            last_checkpoint=working.last_updated
        )
        
    else:
        # Start new content
        trends = await self._get_trending_topics()
        
        await self.update_working_memory(
            title=f"Blog Post: {trends[0]['topic']}",
            description="SEO-optimized blog post about crypto sentiment analysis",
            status="in_progress",
            progress_percent=10,
            next_steps=[
                "Research topic and gather data",
                "Create outline with keywords",
                "Write introduction",
                "Write body sections",
                "Write conclusion and CTA",
                "Optimize for SEO"
            ]
        )


# Example 4: Viewing agent memory via API
"""
# Get full memory context for SCOUT
curl http://localhost:8080/agents/scout/memory

# Get WORKING.md for ORACLE
curl http://localhost:8080/agents/oracle/memory/working

# Get daily notes for SETH
curl http://localhost:8080/agents/seth/memory/daily?date=2025-01-31

# Get long-term memories for ZARA
curl http://localhost:8080/agents/zara/memory/long-term?category=lessons
"""
