/**
 * Ece Face Generation Test Script (Updated for new Higgsfield API)
 * 
 * This script tests the Higgsfield API to generate 5 different face variations
 * for the Ece influencer character using the new async queue-based API.
 * 
 * Usage: node scripts/test-faces.js
 */

const axios = require('axios');
require('dotenv').config({ path: '.env' });

// Configuration
const API_KEY_ID = process.env.HIGGSFIELD_API_KEY_ID;
const API_KEY_SECRET = process.env.HIGGSFIELD_API_KEY_SECRET;
const BASE_URL = process.env.HIGGSFIELD_BASE_URL || 'https://platform.higgsfield.ai';
const MODEL_ID = 'higgsfield-ai/soul/standard';

// Test seeds for Ece face variations
const SEEDS = [55555, 77777, 13131, 20242, 88888];

// Base prompt for Ece character
const BASE_PROMPT = `Portrait of young Turkish woman, 26, olive skin, warm golden undertones, 
dark brown hair messy bun, soft and zen expression, headshot, photorealistic 8k`;

/**
 * Submit a generation request
 */
async function submitRequest(prompt, seed) {
    const endpoint = `${BASE_URL}/${MODEL_ID}`;
    const authHeader = `Key ${API_KEY_ID}:${API_KEY_SECRET}`;
    
    console.log(`\n🎨 Submitting request for seed: ${seed}...`);
    
    try {
        const response = await axios.post(
            endpoint,
            {
                prompt: prompt,
                aspect_ratio: "1:1",
                resolution: "1080p"
            },
            {
                headers: {
                    'Authorization': authHeader,
                    'Content-Type': 'application/json'
                },
                timeout: 30000
            }
        );

        const data = response.data;
        console.log(`✅ Request submitted: ${data.request_id}`);
        console.log(`   Status: ${data.status}`);
        
        return {
            seed: seed,
            requestId: data.request_id,
            statusUrl: data.status_url,
            status: 'submitted'
        };
    } catch (error) {
        console.error(`❌ Seed ${seed} submission failed:`, error.message);
        if (error.response) {
            console.error('   Response:', error.response.data);
        }
        return {
            seed: seed,
            error: error.message,
            status: 'failed'
        };
    }
}

/**
 * Check request status
 */
async function checkStatus(requestId) {
    const endpoint = `${BASE_URL}/requests/${requestId}/status`;
    const authHeader = `Key ${API_KEY_ID}:${API_KEY_SECRET}`;
    
    try {
        const response = await axios.get(endpoint, {
            headers: { 'Authorization': authHeader },
            timeout: 30000
        });
        
        return response.data;
    } catch (error) {
        console.error(`❌ Status check failed for ${requestId}:`, error.message);
        return { status: 'error', error: error.message };
    }
}

/**
 * Wait for request completion
 */
async function waitForCompletion(requestId, seed, maxWaitSeconds = 300) {
    console.log(`⏳ Waiting for seed ${seed} (max ${maxWaitSeconds}s)...`);
    
    const startTime = Date.now();
    const pollInterval = 5000; // 5 seconds
    
    while (true) {
        const statusData = await checkStatus(requestId);
        const status = statusData.status;
        
        if (status === 'completed') {
            // Extract image URL from the images array
            const images = statusData.images || [];
            const imageUrl = images.length > 0 ? images[0].url : null;
            
            console.log(`✅ Seed ${seed} completed!`);
            console.log(`   Image URL: ${imageUrl || 'Not found in response'}`);
            
            return {
                seed: seed,
                requestId: requestId,
                status: 'completed',
                imageUrl: imageUrl,
                fullResponse: statusData
            };
        }
        
        if (status === 'failed') {
            console.error(`❌ Seed ${seed} failed:`, statusData.error || 'Unknown error');
            return {
                seed: seed,
                requestId: requestId,
                status: 'failed',
                error: statusData.error || 'Unknown error'
            };
        }
        
        if (status === 'queued' || status === 'processing' || status === 'in_progress') {
            const elapsed = (Date.now() - startTime) / 1000;
            if (elapsed > maxWaitSeconds) {
                console.error(`⏰ Seed ${seed} timed out after ${elapsed.toFixed(0)}s`);
                return {
                    seed: seed,
                    requestId: requestId,
                    status: 'timeout'
                };
            }
            
            process.stdout.write(`   ${status}... (${elapsed.toFixed(0)}s) \r`);
            await new Promise(resolve => setTimeout(resolve, pollInterval));
        } else {
            console.log(`   Unknown status: ${status}`);
            await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
    }
}

/**
 * Main function to generate all face variations
 */
async function generateAllFaces() {
    console.log('🚀 Ece Face Generation Test (New Higgsfield API)');
    console.log('=================================================');
    console.log(`API Key ID: ${API_KEY_ID ? '✓ Set' : '✗ Missing'}`);
    console.log(`API Key Secret: ${API_KEY_SECRET ? '✓ Set' : '✗ Missing'}`);
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`Model: ${MODEL_ID}`);
    console.log(`Seeds to test: ${SEEDS.join(', ')}`);
    console.log('');

    if (!API_KEY_ID || !API_KEY_SECRET) {
        console.error('❌ HIGGSFIELD_API_KEY_ID or HIGGSFIELD_API_KEY_SECRET is not set in .env file');
        process.exit(1);
    }

    // Step 1: Submit all requests (max 4 concurrent)
    console.log('📤 Step 1: Submitting all requests...\n');
    const submissions = [];
    
    // Submit first 4 requests (max concurrent limit)
    const firstBatch = SEEDS.slice(0, 4);
    for (const seed of firstBatch) {
        const prompt = `${BASE_PROMPT}, variation ${seed}`;
        const result = await submitRequest(prompt, seed);
        submissions.push(result);
        
        // Small delay between submissions
        if (seed !== firstBatch[firstBatch.length - 1]) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    // Step 2: Wait for first batch to complete
    console.log('\n\n⏳ Step 2: Waiting for first batch to complete...\n');
    const results = [];
    
    for (const submission of submissions) {
        if (submission.status === 'submitted') {
            const result = await waitForCompletion(submission.requestId, submission.seed);
            results.push(result);
        } else {
            results.push(submission);
        }
    }

    // Step 3: Submit the 5th request (seed 88888)
    console.log('\n\n📤 Step 3: Submitting remaining request...\n');
    const lastSeed = SEEDS[4];
    const lastPrompt = `${BASE_PROMPT}, variation ${lastSeed}`;
    const lastSubmission = await submitRequest(lastPrompt, lastSeed);
    
    if (lastSubmission.status === 'submitted') {
        const lastResult = await waitForCompletion(lastSubmission.requestId, lastSubmission.seed);
        results.push(lastResult);
    } else {
        results.push(lastSubmission);
    }

    // Summary
    console.log('\n\n📊 Summary');
    console.log('==========');
    
    const successful = results.filter(r => r.status === 'completed');
    const failed = results.filter(r => r.status !== 'completed');
    
    console.log(`Total: ${results.length}`);
    console.log(`Successful: ${successful.length}`);
    console.log(`Failed: ${failed.length}`);
    
    if (successful.length > 0) {
        console.log('\n✅ Successful generations:');
        successful.forEach(r => {
            console.log(`  - Seed ${r.seed}:`);
            console.log(`    Request ID: ${r.requestId}`);
            console.log(`    Image URL: ${r.imageUrl || 'N/A'}`);
        });
        
        console.log('\n💡 Recommendation:');
        console.log('Review the generated images and choose the best one.');
        console.log('Note which seed produced the best result for future use.');
        console.log('\n🖼️  To view the images, copy these URLs to your browser:');
        successful.forEach(r => {
            console.log(`  ${r.imageUrl}`);
        });
    }
    
    if (failed.length > 0) {
        console.log('\n❌ Failed generations:');
        failed.forEach(r => {
            console.log(`  - Seed ${r.seed}: ${r.status} - ${r.error || 'No error details'}`);
        });
    }
    
    // Save results to file
    const fs = require('fs');
    const outputFile = 'ece-face-results.json';
    fs.writeFileSync(outputFile, JSON.stringify(results, null, 2));
    console.log(`\n💾 Results saved to: ${outputFile}`);
}

// Run the script
generateAllFaces().catch(error => {
    console.error('Unexpected error:', error);
    process.exit(1);
});
