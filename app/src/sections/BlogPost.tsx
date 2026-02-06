import { useParams, Link, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { format } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Clock, Calendar, ArrowLeft, Share2, Twitter, Linkedin } from 'lucide-react';
import { samplePosts } from '../data/samplePosts';
import CategoryBadge from '../components/blog/CategoryBadge';
import PostCard from '../components/blog/PostCard';

import 'highlight.js/styles/github-dark.css';

const BlogPost = () => {
  const { slug } = useParams<{ slug: string }>();
  const post = samplePosts.find((p) => p.slug === slug);

  useEffect(() => {
    if (post) {
      // Set page title
      document.title = post.seo.metaTitle;

      // Set meta description
      const metaDescription = document.querySelector('meta[name="description"]');
      if (metaDescription) {
        metaDescription.setAttribute('content', post.seo.metaDescription);
      }

      // Scroll to top
      window.scrollTo(0, 0);
    }
  }, [post]);

  if (!post) {
    return <Navigate to="/blog" replace />;
  }

  const relatedPosts = samplePosts
    .filter((p) => p.id !== post.id && p.category === post.category)
    .slice(0, 2);

  const shareUrl = `https://sentilyze.live/blog/${post.slug}`;
  const shareText = encodeURIComponent(post.title);

  // JSON-LD Schema for SEO
  const schemaData = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": post.title,
    "description": post.seo.metaDescription,
    "image": post.coverImage || "https://sentilyze.live/favicon.svg",
    "datePublished": post.publishedAt,
    "dateModified": post.publishedAt,
    "author": {
      "@type": "Person",
      "name": post.author.name
    },
    "publisher": {
      "@type": "Organization",
      "name": "Sentilyze",
      "logo": {
        "@type": "ImageObject",
        "url": "https://sentilyze.live/favicon.svg"
      }
    },
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": shareUrl
    },
    "wordCount": Math.floor(post.content.split(' ').length)
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <Helmet>
        <title>{post.seo.metaTitle}</title>
        <meta name="description" content={post.seo.metaDescription} />
        <meta name="keywords" content={post.seo.keywords.join(', ')} />

        {/* Open Graph Tags for Social Sharing */}
        <meta property="og:type" content="article" />
        <meta property="og:title" content={post.seo.metaTitle} />
        <meta property="og:description" content={post.seo.metaDescription} />
        <meta property="og:url" content={shareUrl} />
        <meta property="og:image" content={post.coverImage || "https://sentilyze.live/favicon.svg"} />
        <meta property="article:published_time" content={post.publishedAt} />
        <meta property="article:author" content={post.author.name} />

        {/* Twitter Card Tags */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={post.seo.metaTitle} />
        <meta name="twitter:description" content={post.seo.metaDescription} />
        <meta name="twitter:image" content={post.coverImage || "https://sentilyze.live/favicon.svg"} />

        {/* Canonical URL */}
        <link rel="canonical" href={shareUrl} />

        {/* JSON-LD Schema */}
        <script type="application/ld+json">{JSON.stringify(schemaData)}</script>
      </Helmet>

      {/* Back Button */}
      <div className="border-b border-[var(--border-color)]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link
            to="/blog"
            className="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--gold-primary)] transition-colors"
          >
            <ArrowLeft size={20} />
            <span>Back to Blog</span>
          </Link>
        </div>
      </div>

      {/* Article Header */}
      <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <header className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <CategoryBadge category={post.category} />
            {post.featured && (
              <span className="px-3 py-1 text-sm font-medium rounded-full bg-[var(--gold-light)] text-[var(--gold-primary)] border border-[var(--gold-primary)]/30">
                Featured
              </span>
            )}
          </div>

          <h1 className="text-4xl sm:text-5xl font-bold text-[var(--text-primary)] mb-6 leading-tight">
            {post.title}
          </h1>

          <div className="flex flex-wrap items-center gap-6 text-sm text-[var(--text-muted)] mb-6">
            <div className="flex items-center gap-2">
              <Calendar size={16} />
              <span>{format(new Date(post.publishedAt), 'MMMM d, yyyy')}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock size={16} />
              <span>{post.readingTime} min read</span>
            </div>
            <div className="flex items-center gap-2">
              <span>By {post.author.name}</span>
            </div>
          </div>

          {/* Share Buttons */}
          <div className="flex items-center gap-4 pt-6 border-t border-[var(--border-color)]">
            <span className="text-sm text-[var(--text-muted)]">Share:</span>
            <a
              href={`https://twitter.com/intent/tweet?text=${shareText}&url=${shareUrl}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] text-[var(--text-secondary)] hover:text-[#1DA1F2] transition-colors"
              aria-label="Share on Twitter"
            >
              <Twitter size={18} />
            </a>
            <a
              href={`https://www.linkedin.com/sharing/share-offsite/?url=${shareUrl}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] text-[var(--text-secondary)] hover:text-[#0A66C2] transition-colors"
              aria-label="Share on LinkedIn"
            >
              <Linkedin size={18} />
            </a>
            <button
              onClick={() => {
                navigator.clipboard.writeText(shareUrl);
                alert('Link copied to clipboard!');
              }}
              className="p-2 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] text-[var(--text-secondary)] hover:text-[var(--gold-primary)] transition-colors"
              aria-label="Copy link"
            >
              <Share2 size={18} />
            </button>
          </div>
        </header>

        {/* Article Content */}
        <div className="prose prose-invert prose-lg max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              h1: ({ children }) => (
                <h1 className="text-3xl font-bold text-[var(--text-primary)] mt-8 mb-4">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-8 mb-4">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-xl font-semibold text-[var(--text-primary)] mt-6 mb-3">
                  {children}
                </h3>
              ),
              p: ({ children }) => (
                <p className="text-[var(--text-secondary)] leading-relaxed mb-4">
                  {children}
                </p>
              ),
              a: ({ href, children }) => (
                <a
                  href={href}
                  className="text-[var(--gold-primary)] hover:underline"
                  target={href?.startsWith('http') ? '_blank' : undefined}
                  rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
                >
                  {children}
                </a>
              ),
              code: ({ children, className }) => {
                const isInline = !className;
                return isInline ? (
                  <code className="px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] text-[var(--gold-primary)] text-sm font-mono">
                    {children}
                  </code>
                ) : (
                  <code className={className}>{children}</code>
                );
              },
              pre: ({ children }) => (
                <pre className="bg-[#0d1117] rounded-lg p-4 overflow-x-auto my-6 border border-[var(--border-color)]">
                  {children}
                </pre>
              ),
              ul: ({ children }) => (
                <ul className="list-disc list-inside space-y-2 mb-4 text-[var(--text-secondary)]">
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside space-y-2 mb-4 text-[var(--text-secondary)]">
                  {children}
                </ol>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-[var(--gold-primary)] pl-4 italic text-[var(--text-secondary)] my-6">
                  {children}
                </blockquote>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto my-6">
                  <table className="min-w-full border border-[var(--border-color)] rounded-lg">
                    {children}
                  </table>
                </div>
              ),
              th: ({ children }) => (
                <th className="px-4 py-2 bg-[var(--bg-secondary)] text-left text-[var(--text-primary)] font-semibold border-b border-[var(--border-color)]">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-4 py-2 border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                  {children}
                </td>
              ),
            }}
          >
            {post.content}
          </ReactMarkdown>
        </div>

        {/* Tags */}
        {post.tags.length > 0 && (
          <div className="mt-12 pt-8 border-t border-[var(--border-color)]">
            <div className="flex flex-wrap gap-2">
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1 text-sm rounded-full bg-[var(--bg-secondary)] text-[var(--text-muted)] border border-[var(--border-color)]"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </article>

      {/* Related Posts */}
      {relatedPosts.length > 0 && (
        <section className="border-t border-[var(--border-color)] py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-8">
              Related Articles
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {relatedPosts.map((relatedPost) => (
                <PostCard key={relatedPost.id} post={relatedPost} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* CTA Section */}
      <section className="bg-[var(--bg-secondary)] border-t border-[var(--border-color)] py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h3 className="text-3xl font-bold text-[var(--text-primary)] mb-4">
            Ready to Start Analyzing?
          </h3>
          <p className="text-lg text-[var(--text-secondary)] mb-8">
            Experience AI-powered market sentiment analysis and price predictions.
          </p>
          <Link
            to="/app"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl font-semibold bg-gradient-to-r from-[var(--gold-primary)] to-[var(--gold-soft)] hover:from-[var(--gold-hover)] hover:to-[var(--gold-primary)] transition-all duration-300 shadow-lg hover:shadow-2xl hover:shadow-[var(--gold-primary)]/50 hover:scale-105 text-[var(--bg-primary)]"
          >
            Start Free Analysis
          </Link>
        </div>
      </section>
    </div>
  );
};

export default BlogPost;
