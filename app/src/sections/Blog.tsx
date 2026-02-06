import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { samplePosts } from '../data/samplePosts';
import PostCard from '../components/blog/PostCard';
import CategoryBadge from '../components/blog/CategoryBadge';
import { BookOpen } from 'lucide-react';

const Blog = () => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const filteredPosts = selectedCategory
    ? samplePosts.filter((post) => post.category === selectedCategory)
    : samplePosts;

  const featuredPosts = samplePosts.filter((post) => post.featured);
  const categories: Array<'crypto' | 'gold' | 'ai-ml' | 'trading'> = ['crypto', 'gold', 'ai-ml', 'trading'];

  const schemaData = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Sentilyze Blog - AI Market Analysis & Trading Insights",
    "description": "Read in-depth articles on cryptocurrency markets, gold analysis, AI-powered trading strategies, and machine learning insights.",
    "url": "https://sentilyze.live/blog",
    "mainEntity": {
      "@type": "Blog",
      "name": "Sentilyze Blog",
      "description": "AI-powered market analysis and trading insights"
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <Helmet>
        <title>Sentilyze Blog - AI Market Analysis, Gold, Crypto Insights</title>
        <meta name="description" content="Explore in-depth articles on cryptocurrency markets, gold analysis, AI-powered trading strategies, and machine learning insights." />
        <meta name="keywords" content="AI trading, market analysis, gold prices, cryptocurrency insights, machine learning trading, sentiment analysis" />
        <link rel="canonical" href="https://sentilyze.live/blog" />

        {/* Open Graph */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content="Sentilyze Blog - AI Market Analysis & Trading Insights" />
        <meta property="og:description" content="Explore in-depth articles on cryptocurrency markets, gold analysis, AI-powered trading strategies, and machine learning insights." />
        <meta property="og:url" content="https://sentilyze.live/blog" />
        <meta property="og:image" content="https://sentilyze.live/favicon.svg" />

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Sentilyze Blog" />
        <meta name="twitter:description" content="AI-powered market analysis and insights" />

        {/* JSON-LD */}
        <script type="application/ld+json">{JSON.stringify(schemaData)}</script>
      </Helmet>

      {/* Hero Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8 border-b border-[var(--border-color)]">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--gold-light)] border border-[var(--gold-primary)]/30 mb-6">
            <BookOpen className="w-4 h-4 text-[var(--gold-primary)]" />
            <span className="text-sm font-semibold text-[var(--gold-primary)]">
              Insights & Analysis
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-[var(--text-primary)] mb-6">
            Sentilyze <span className="text-[var(--gold-primary)]">Blog</span>
          </h1>

          <p className="text-lg text-[var(--text-secondary)] max-w-3xl mx-auto">
            Explore in-depth articles on cryptocurrency markets, gold analysis, AI-powered trading strategies, and machine learning insights.
          </p>
        </div>
      </section>

      {/* Category Filter */}
      <section className="sticky top-0 z-10 bg-[var(--bg-primary)]/95 backdrop-blur-lg border-b border-[var(--border-color)] py-4 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 overflow-x-auto pb-2">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`px-4 py-2 rounded-lg font-medium text-sm whitespace-nowrap transition-all ${
                selectedCategory === null
                  ? 'bg-[var(--gold-primary)] text-[var(--bg-primary)]'
                  : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
              }`}
            >
              All Posts
            </button>
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-all ${
                  selectedCategory === category
                    ? 'ring-2 ring-[var(--gold-primary)]'
                    : 'hover:bg-[var(--bg-hover)]'
                }`}
              >
                <CategoryBadge category={category} size="sm" />
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Posts */}
      {!selectedCategory && featuredPosts.length > 0 && (
        <section className="py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">
              Featured Articles
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {featuredPosts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* All Posts */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">
            {selectedCategory ? `${selectedCategory.toUpperCase()} Articles` : 'All Articles'}
          </h2>

          {filteredPosts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {filteredPosts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-[var(--text-muted)]">
                No articles found in this category yet.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default Blog;
