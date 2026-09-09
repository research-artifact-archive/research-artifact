/*
 * Copyright (c) 2014, Oracle America, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 *  * Neither the name of Oracle nor the names of its contributors may be used
 *    to endorse or promote products derived from this software without
 *    specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGE.
 */

package org.anonymous.retry;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.function.BiFunction;
import org.openjdk.jmh.annotations.*;

/** Author microbenchmark of the named API paths, not an adversarial policy run. */
@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 3, time = 200, timeUnit = TimeUnit.MILLISECONDS)
@Measurement(iterations = 5, time = 200, timeUnit = TimeUnit.MILLISECONDS)
@Fork(value = 2, jvmArgsAppend = {"-Xms256m", "-Xmx256m", "-ea"})
@Threads(1)
public class MyBenchmark {
    @Param({"1", "8", "64", "512"}) public int length;
    @Param({"distinct", "colliding"}) public String layout;

    public static final class Key {
        final int hash;
        Key(int hash) { this.hash = hash; }
        @Override public int hashCode() { return hash; }
    }

    public static final class Value {
        final long version;
        final int[] data;
        final int checksum;
        Value(long version, int[] data, int checksum) {
            this.version = version; this.data = data; this.checksum = checksum;
        }
    }

    private ConcurrentHashMap<Key, Value> map;
    private Key target;
    private Value tokenA, tokenB, stale, cursor, before, prepared;
    private BiFunction<Key, Value, Value> validator, transformer, cachedCompleter;

    @Setup(Level.Trial)
    public void setup() {
        int[] data = new int[length];
        int checksum = 0;
        for (int i = 0; i < length; ++i) { data[i] = 17 + 31 * i; checksum = 31 * checksum + data[i]; }
        tokenA = new Value(0, data, checksum);
        tokenB = new Value(1, data.clone(), checksum);
        stale = new Value(-1, data.clone(), checksum);
        cursor = tokenA;
        map = new ConcurrentHashMap<>(128);
        for (int i = 0; i < 8; ++i) {
            Key key = new Key(layout.equals("colliding") ? 0 : i);
            map.put(key, tokenA);
            if (i == 7) { target = key; }
        }
        validator = (key, source) -> source == before ? prepared : source;
        transformer = (key, source) -> transform(source);
        cachedCompleter = (key, source) -> source == before ? prepared : transform(source);
    }

    /** Same full-array transformation both inside and outside the native bin monitor. */
    private Value transform(Value source) {
        int[] output = new int[source.data.length];
        int checksum = 0;
        for (int i = 0; i < output.length; ++i) {
            output[i] = 1664525 * source.data[i] + 1013904223;
            checksum = 31 * checksum + output[i];
        }
        return new Value(source.version + 1, output, checksum);
    }

    @Benchmark public Value get() { return map.get(target); }
    @Benchmark public Value prepare() { return transform(map.get(target)); }

    @Benchmark public boolean replaceMatch() {
        Value next = cursor == tokenA ? tokenB : tokenA;
        boolean matched = map.replace(target, cursor, next);
        cursor = next;
        return matched;
    }

    @Benchmark public boolean replaceMismatch() { return map.replace(target, stale, tokenB); }

    @Benchmark public Value validateCallbackMatch() {
        before = cursor;
        prepared = cursor == tokenA ? tokenB : tokenA;
        Value result = map.compute(target, validator);
        cursor = result;
        return result;
    }

    @Benchmark public Value validateCallbackMismatch() {
        before = stale;
        prepared = tokenB;
        return map.compute(target, validator);
    }

    @Benchmark public Value freshCallback() { return map.compute(target, transformer); }

    @Benchmark public Value cachedCallbackMatch() {
        before = cursor;
        prepared = cursor == tokenA ? tokenB : tokenA;
        Value result = map.compute(target, cachedCompleter);
        cursor = result;
        return result;
    }

    @Benchmark public Value cachedCallbackMismatch() {
        before = stale;
        prepared = tokenB;
        return map.compute(target, cachedCompleter);
    }
}
