package glim.tk;

import com.andrei1058.bedwars.api.BedWars;
import com.andrei1058.bedwars.api.arena.GameState;
import com.andrei1058.bedwars.api.arena.IArena;
import com.andrei1058.bedwars.api.arena.shop.ICategoryContent;
import com.andrei1058.bedwars.api.arena.shop.IContentTier;
import com.andrei1058.bedwars.api.arena.team.ITeam;
import com.andrei1058.bedwars.api.events.gameplay.GameEndEvent;
import com.andrei1058.bedwars.api.events.gameplay.GameStateChangeEvent;
import com.andrei1058.bedwars.api.events.player.PlayerBedBreakEvent;
import com.andrei1058.bedwars.api.events.player.PlayerKillEvent;
import com.andrei1058.bedwars.api.events.shop.ShopBuyEvent;
import com.andrei1058.bedwars.api.events.upgrades.UpgradeBuyEvent;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.OfflinePlayer;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.command.RemoteConsoleCommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Projectile;
import org.bukkit.entity.TNTPrimed;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerPickupItemEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.projectiles.ProjectileSource;
import org.bukkit.util.Vector;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

/**
 * GlimTruthKit: Glim's server-side truth log for Bedwars (a copy of the older PlayKit plugin, renamed and extended; PlayKit itself
 * is not touched). It writes ONE file, logs/truth.jsonl in our glim-bedwars folder: one JSON object per line, ms timestamps.
 *   every line: {"ms": epoch ms, "t": "yyyy-MM-ddTHH:mm:ss.SSS+hh:mm" (same instant), "type": ..., ...}
 *   types: join, leave, match_start, match_end, hit, death, kill, void_death, bed_broken, purchase, upgrade, pickup, block_place,
 *          block_break, tick (20 Hz while a match plays: position, velocity, on-ground per player), edge (feet leave the last block).
 * It also sends GlimBot-like players (autojoin-regex) into the autojoin arena on login (no chat typing) and has console/RCON
 * commands to join, force-start (BedWars1058's own "/bw forceStart debug", run as the player in the arena), stop and nudge.
 * Human chat text is never stored (not here, not in the console log: the console filter from PlayKit is kept).
 * License: written for this project; links against the Bukkit/Paper API and the BedWars1058 API (GPL-3.0) -> GPL-3.0.
 */
public class TruthKit extends JavaPlugin implements Listener {
    BedWars bw;
    Pattern botRx;                 // names Glim controls (auto-joined, may be force-started); everyone else is a human
    volatile String autojoin = "";
    File truthFile, autojoinFile;
    long maxBytes;
    boolean ticksOn = true;
    final Map<String, Match> matches = new HashMap<>();
    final LinkedBlockingQueue<Object[]> q = new LinkedBlockingQueue<>();   // {Long ms, String body}
    Thread wt;
    volatile boolean running = true;
    long tickNo = 0;

    static final class Match { String id, arena; long startMs, tick0; boolean ended; final Map<UUID, double[]> prev = new HashMap<>(); final Map<UUID, EdgeSt> edge = new HashMap<>(); }
    static final class EdgeSt { boolean has, supported; double groundY, px, pz; long lastSupMs; }
    static final class DeathRec { long ms; String victim, killer, cause, arena; boolean fin, isVoid, fromBw; }
    final Map<String, DeathRec> pendingDeaths = new HashMap<>();

    // ------------------------------------------------------------ lifecycle
    @Override public void onEnable() {
        saveDefaultConfig();
        botRx = Pattern.compile(getConfig().getString("autojoin-regex", "^Glim[A-Za-z0-9_]*$"));
        ticksOn = getConfig().getBoolean("ticks", true);
        maxBytes = Math.max(1, getConfig().getInt("truth-max-mb", 64)) * 1024L * 1024L;
        String tf = getConfig().getString("truth-file", "C:/Users/benja/glim-bedwars/logs/truth.jsonl");
        truthFile = new File(tf).isAbsolute() ? new File(tf) : new File(getServer().getWorldContainer(), tf);
        truthFile.getParentFile().mkdirs();
        getDataFolder().mkdirs();
        autojoinFile = new File(getDataFolder(), "autojoin.txt");
        autojoin = readAutojoin();
        installConsoleFilter();
        bw = Bukkit.getServicesManager().getRegistration(BedWars.class).getProvider();
        Bukkit.getPluginManager().registerEvents(this, this);
        wt = new Thread(this::writerLoop, "glimtruthkit-writer"); wt.setDaemon(true); wt.start();
        Bukkit.getScheduler().runTaskTimer(this, this::onTick, 1L, 1L);
        getLogger().info("GlimTruthKit on: truth=" + truthFile + " autojoin='" + autojoin + "' ticks=" + ticksOn);
    }
    @Override public void onDisable() {
        for (Match m : new ArrayList<>(matches.values())) endMatch(m, "", new ArrayList<String>(), "server stop");
        running = false;
        try { wt.join(3000); } catch (InterruptedException ignored) { }
    }

    String readAutojoin() {
        try { if (autojoinFile.exists()) { String s = new String(Files.readAllBytes(autojoinFile.toPath()), StandardCharsets.UTF_8).trim(); if (s.matches("^[A-Za-z0-9_\\-]{0,32}$")) return s; } }
        catch (Exception e) { getLogger().warning("autojoin.txt: " + e); }
        return getConfig().getString("autojoin", "");
    }
    void setAutojoin(String a) {
        autojoin = a;
        try { Files.write(autojoinFile.toPath(), a.getBytes(StandardCharsets.UTF_8)); } catch (Exception e) { getLogger().warning("autojoin.txt: " + e); }
    }

    // ------------------------------------------------------------ writer thread (ms is taken on the main thread when the thing happens)
    void ev(String type, J body) { ev(System.currentTimeMillis(), type, body); }
    void ev(long ms, String type, J body) { q.add(new Object[]{ms, "\"type\":" + js(type) + body.b}); }
    void writerLoop() {
        SimpleDateFormat iso = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX");
        BufferedWriter w = null; long lastFlush = 0, size = 0;
        while (running || !q.isEmpty()) {
            try {
                Object[] it = q.poll(100, TimeUnit.MILLISECONDS);
                if (it != null) {
                    if (w == null) { w = open(); size = truthFile.length(); }
                    long ms = (Long) it[0];
                    String line = "{\"ms\":" + ms + ",\"t\":\"" + iso.format(new Date(ms)) + "\"," + it[1] + "}\n";
                    w.write(line); size += line.length();
                    if (size > maxBytes) {   // rotate our own log: truth.jsonl -> truth.prev.jsonl (the previous .prev is replaced)
                        w.close(); w = null;
                        File prev = new File(truthFile.getParentFile(), "truth.prev.jsonl");
                        Files.move(truthFile.toPath(), prev.toPath(), StandardCopyOption.REPLACE_EXISTING);
                    }
                }
                long now = System.currentTimeMillis();
                if (w != null && now - lastFlush >= 200) { lastFlush = now; w.flush(); }
            } catch (Exception e) { getLogger().warning("writer: " + e); w = null; }
        }
        try { if (w != null) w.close(); } catch (Exception ignored) { }
    }
    BufferedWriter open() throws Exception { return new BufferedWriter(new OutputStreamWriter(new FileOutputStream(truthFile, true), StandardCharsets.UTF_8), 1 << 16); }

    // ------------------------------------------------------------ json helpers
    static String js(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder(s.length() + 2).append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        return b.append('"').toString();
    }
    static String f(double v) { return Double.isNaN(v) || Double.isInfinite(v) ? "0" : String.format(Locale.ROOT, "%.3f", v); }
    static final class J {   // appends ,"k":v pairs
        final StringBuilder b = new StringBuilder(128);
        J s(String k, String v) { b.append(",\"").append(k).append("\":").append(js(v)); return this; }
        J n(String k, double v) { b.append(",\"").append(k).append("\":").append(f(v)); return this; }
        J i(String k, long v) { b.append(",\"").append(k).append("\":").append(v); return this; }
        J z(String k, boolean v) { b.append(",\"").append(k).append("\":").append(v); return this; }
        J raw(String k, String json) { b.append(",\"").append(k).append("\":").append(json); return this; }
    }
    static String arr(Collection<String> xs) { StringBuilder b = new StringBuilder("["); boolean f = true; for (String x : xs) { if (!f) b.append(','); f = false; b.append(js(x)); } return b.append(']').toString(); }
    static String lower(Material m) { return m == null ? "" : m.name().toLowerCase(Locale.ROOT); }

    // ------------------------------------------------------------ arena helpers
    IArena arenaOf(Player p) { return p == null ? null : bw.getArenaUtil().getArenaByPlayer(p); }
    static String st(GameState s) { return s == null ? "" : s.name(); }
    static String teamName(ITeam t) { return t == null ? "" : t.getName(); }
    boolean aliveIn(IArena a, Player p) { return a.isPlayer(p) && !a.isSpectator(p) && !a.isReSpawning(p.getUniqueId()); }

    // ------------------------------------------------------------ join / leave + auto-join (no chat typing: performCommand runs as the player)
    @EventHandler public void onJoin(PlayerJoinEvent e) {
        final Player p = e.getPlayer();
        ev("join", new J().s("player", p.getName()));
        if (autojoin.isEmpty() || !botRx.matcher(p.getName()).matches()) return;
        for (long delay : new long[]{30L, 160L}) {
            Bukkit.getScheduler().runTaskLater(this, new Runnable() { public void run() {
                if (!autojoin.isEmpty() && p.isOnline() && arenaOf(p) == null) { getLogger().info("auto-join " + p.getName() + " -> " + autojoin); p.performCommand("bw join " + autojoin); }
            } }, delay);
        }
    }
    @EventHandler public void onQuit(PlayerQuitEvent e) { ev("leave", new J().s("player", e.getPlayer().getName())); }

    // ------------------------------------------------------------ match lifecycle
    @EventHandler public void onState(GameStateChangeEvent e) {
        IArena a = e.getArena();
        if (e.getNewState() == GameState.playing && !matches.containsKey(a.getArenaName())) startMatch(a);
        Match m = matches.get(a.getArenaName());
        if (m != null && e.getNewState() == GameState.restarting) endMatch(m, "", new ArrayList<String>(), "restarting");
    }
    @EventHandler public void onEnd(GameEndEvent e) {
        Match m = matches.get(e.getArena().getArenaName()); if (m == null) return;
        List<String> names = new ArrayList<>();
        for (UUID u : e.getWinners()) { OfflinePlayer op = Bukkit.getOfflinePlayer(u); if (op != null && op.getName() != null) names.add(op.getName()); }
        endMatch(m, teamName(e.getTeamWinner()), names, "game end");
    }
    void startMatch(IArena a) {
        Match m = new Match();
        m.arena = a.getArenaName(); m.startMs = System.currentTimeMillis(); m.tick0 = tickNo;
        m.id = new SimpleDateFormat("yyyyMMdd-HHmmss").format(new Date(m.startMs)) + "-" + a.getArenaName();
        matches.put(a.getArenaName(), m);
        StringBuilder t = new StringBuilder("[");
        boolean first = true;
        for (ITeam tm : a.getTeams()) {
            if (!first) t.append(','); first = false;
            List<String> mem = new ArrayList<>(); for (Player p : tm.getMembers()) mem.add(p.getName());
            Location b = tm.getBed();
            t.append("{\"team\":").append(js(tm.getName())).append(",\"members\":").append(arr(mem));
            if (b != null) t.append(",\"bed\":[").append(f(b.getX())).append(',').append(f(b.getY())).append(',').append(f(b.getZ())).append(']');
            t.append('}');
        }
        t.append(']');
        ev(m.startMs, "match_start", new J().s("arena", a.getArenaName()).s("match_id", m.id).s("group", String.valueOf(a.getGroup())).raw("teams", t.toString()));
        getLogger().info("truth: match_start " + m.id);
    }
    void endMatch(Match m, String winnerTeam, List<String> winners, String why) {
        if (m.ended) return;
        m.ended = true; matches.remove(m.arena);
        ev("match_end", new J().s("arena", m.arena).s("match_id", m.id).s("winner_team", winnerTeam).raw("winners", arr(winners)).s("why", why).i("ticks", tickNo - m.tick0));
        getLogger().info("truth: match_end " + m.id + " (" + why + ")");
    }

    // ------------------------------------------------------------ per tick: positions (20 Hz) + edge
    void onTick() {
        tickNo++;
        if (matches.isEmpty()) return;
        for (Match m : new ArrayList<>(matches.values())) {
            IArena a = bw.getArenaUtil().getArenaByName(m.arena);
            if (a == null || a.getStatus() != GameState.playing) continue;
            snapshot(m, a);
        }
    }
    void snapshot(Match m, IArena a) {
        long now = System.currentTimeMillis();
        StringBuilder b = new StringBuilder(512).append('[');
        boolean first = true;
        List<Player> all = new ArrayList<>(a.getPlayers());
        for (Player s : a.getSpectators()) if (!all.contains(s)) all.add(s);
        for (Player p : all) {
            Location l = p.getLocation();
            double[] pv = m.prev.get(p.getUniqueId());
            boolean tele = pv != null && (Math.abs(l.getX() - pv[0]) > 2 || Math.abs(l.getY() - pv[1]) > 4 || Math.abs(l.getZ() - pv[2]) > 2);
            double vx = 0, vy = 0, vz = 0;
            if (pv != null && !tele) { vx = (l.getX() - pv[0]) * 20; vy = (l.getY() - pv[1]) * 20; vz = (l.getZ() - pv[2]) * 20; }
            m.prev.put(p.getUniqueId(), new double[]{l.getX(), l.getY(), l.getZ()});
            boolean alive = aliveIn(a, p), og = p.isOnGround();
            edgeCheck(m, p, l, og, alive, tele, vx, vz, now);
            if (!ticksOn) continue;
            ItemStack h = p.getItemInHand();
            if (!first) b.append(','); first = false;
            b.append("{\"n\":").append(js(p.getName())).append(",\"team\":").append(js(teamName(a.getTeam(p))))
             .append(",\"x\":").append(f(l.getX())).append(",\"y\":").append(f(l.getY())).append(",\"z\":").append(f(l.getZ()))
             .append(",\"yaw\":").append(f(l.getYaw())).append(",\"pitch\":").append(f(l.getPitch()))
             .append(",\"vx\":").append(f(vx)).append(",\"vy\":").append(f(vy)).append(",\"vz\":").append(f(vz))
             .append(",\"og\":").append(og ? 1 : 0).append(",\"alive\":").append(alive ? 1 : 0)
             .append(",\"hp\":").append(f(p.getHealth())).append(",\"sneak\":").append(p.isSneaking() ? 1 : 0).append(",\"sprint\":").append(p.isSprinting() ? 1 : 0)
             .append(",\"held\":").append(js(h == null ? "" : lower(h.getType()))).append('}');
        }
        b.append(']');
        if (ticksOn) ev(now, "tick", new J().s("arena", m.arena).i("tick", tickNo - m.tick0).raw("p", b.toString()));
    }
    /** edge = the first tick at which the feet footprint (x +- 0.3, z +- 0.3) no longer overlaps any solid block at the last ground level
     *  (also mid-jump: the moment the player crosses the edge). last_supported_ms = the tick before (the latest moment still over the block). */
    void edgeCheck(Match m, Player p, Location l, boolean og, boolean alive, boolean tele, double vx, double vz, long now) {
        EdgeSt s = m.edge.get(p.getUniqueId());
        if (s == null) { s = new EdgeSt(); m.edge.put(p.getUniqueId(), s); }
        s.px = l.getX(); s.pz = l.getZ();
        if (!alive || tele) { s.has = false; s.supported = false; return; }
        if (og) { s.groundY = l.getY(); s.has = true; }
        if (!s.has) return;
        if (l.getY() < s.groundY - 2.0) { s.supported = false; return; }   // already falling well below: no new edge until ground again
        boolean sup = supported(l.getWorld(), l.getX(), s.groundY, l.getZ());
        if (s.supported && !sup)
            ev(now, "edge", new J().s("player", p.getName()).s("arena", m.arena).n("x", l.getX()).n("y", l.getY()).n("z", l.getZ())
                    .n("ground_y", s.groundY).i("og", og ? 1 : 0).n("vx", vx).n("vz", vz).i("last_supported_ms", s.lastSupMs));
        if (sup) s.lastSupMs = now;
        s.supported = sup;
    }
    static boolean supported(World w, double x, double gy, double z) {
        int by = (int) Math.floor(gy - 0.01);
        int x0 = (int) Math.floor(x - 0.3), x1 = (int) Math.floor(x + 0.3 - 1e-6), z0 = (int) Math.floor(z - 0.3), z1 = (int) Math.floor(z + 0.3 - 1e-6);
        for (int bx = x0; bx <= x1; bx++) for (int bz = z0; bz <= z1; bz++) if (w.getBlockAt(bx, by, bz).getType().isSolid()) return true;
        return false;
    }

    // ------------------------------------------------------------ hits (crit = 1.8 rule, checked on the attacker at the moment of the hit)
    static boolean critNow(Player a) {
        if (a.isOnGround() || a.getFallDistance() <= 0f || a.isInsideVehicle() || a.hasPotionEffect(PotionEffectType.BLINDNESS)) return false;
        Material m = a.getLocation().getBlock().getType();
        return !(m == Material.LADDER || m == Material.VINE || m == Material.WATER || m == Material.STATIONARY_WATER);
    }
    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onDamage(EntityDamageByEntityEvent e) {
        if (!(e.getEntity() instanceof Player)) return;
        Player v = (Player) e.getEntity();
        Entity d = e.getDamager(); Player a = null; String via = "melee";
        if (d instanceof Player) a = (Player) d;
        else if (d instanceof Projectile) { ProjectileSource s = ((Projectile) d).getShooter(); if (s instanceof Player) { a = (Player) s; via = d.getType().name().toLowerCase(Locale.ROOT); } }
        else if (d instanceof TNTPrimed) { Entity src = ((TNTPrimed) d).getSource(); if (src instanceof Player) { a = (Player) src; via = "tnt"; } }
        if (a == null || a == v) return;
        IArena ar = arenaOf(v); if (ar == null) ar = arenaOf(a); if (ar == null) return;
        boolean crit = "melee".equals(via) && critNow(a);
        ev("hit", new J().s("attacker", a.getName()).s("victim", v.getName()).n("damage", e.getFinalDamage()).n("raw_damage", e.getDamage())
                .z("crit", crit).s("via", via).n("victim_hp", v.getHealth()).s("arena", ar.getArenaName()));
    }

    // ------------------------------------------------------------ deaths: BedWars1058's kill event + Bukkit's death event, merged per victim
    void noteDeath(Player victim, String killer, String cause, boolean fin, boolean isVoid, IArena a, boolean fromBw) {
        final String vn = victim.getName();
        DeathRec d = pendingDeaths.get(vn);
        if (d == null) {
            d = new DeathRec(); d.ms = System.currentTimeMillis(); d.victim = vn; pendingDeaths.put(vn, d);
            Bukkit.getScheduler().runTaskLater(this, new Runnable() { public void run() { flushDeath(vn); } }, 2L);
        }
        if (fromBw) { d.fromBw = true; if (killer != null) d.killer = killer; d.cause = cause; d.fin = fin; }
        else { if (d.killer == null) d.killer = killer; if (d.cause == null) d.cause = cause; }
        d.isVoid |= isVoid;
        if (d.arena == null && a != null) d.arena = a.getArenaName();
    }
    void flushDeath(String vn) {
        DeathRec d = pendingDeaths.remove(vn); if (d == null) return;
        String k = d.killer != null && !d.killer.isEmpty() && !d.killer.equals(d.victim) ? d.killer : null;
        ev(d.ms, "death", new J().s("victim", d.victim).s("killer", k).s("cause", d.cause).z("final", d.fin).z("void", d.isVoid).s("arena", d.arena));
        if (k != null) ev(d.ms, "kill", new J().s("killer", k).s("victim", d.victim).s("cause", d.cause).z("final", d.fin).z("void", d.isVoid).s("arena", d.arena));
        if (d.isVoid) ev(d.ms, "void_death", new J().s("victim", d.victim).s("killer", k).z("final", d.fin).s("arena", d.arena));
    }
    @EventHandler(priority = EventPriority.MONITOR) public void onKill(PlayerKillEvent e) {
        Player v = e.getVictim(); if (v == null) return;
        PlayerKillEvent.PlayerKillCause c = e.getCause();
        String cause = c == null ? "UNKNOWN" : c.name();
        noteDeath(v, e.getKiller() == null ? null : e.getKiller().getName(), cause, c != null && c.isFinalKill(), cause.startsWith("VOID"), e.getArena(), true);
    }
    @EventHandler(priority = EventPriority.MONITOR) public void onDeath(PlayerDeathEvent e) {
        Player v = e.getEntity(); IArena a = arenaOf(v); if (a == null) return;
        EntityDamageEvent ld = v.getLastDamageCause();
        String cause = ld == null ? "UNKNOWN" : ld.getCause().name();
        noteDeath(v, v.getKiller() == null ? null : v.getKiller().getName(), cause, false, ld != null && ld.getCause() == EntityDamageEvent.DamageCause.VOID, a, false);
    }

    // ------------------------------------------------------------ bed, shop, upgrades, pickups, blocks
    @EventHandler(priority = EventPriority.MONITOR) public void onBed(PlayerBedBreakEvent e) {
        ev("bed_broken", new J().s("by", e.getPlayer() == null ? null : e.getPlayer().getName()).s("by_team", teamName(e.getPlayerTeam()))
                .s("team", teamName(e.getVictimTeam())).s("arena", e.getArena().getArenaName()));
    }
    @EventHandler(priority = EventPriority.MONITOR) public void onShop(ShopBuyEvent e) {
        if (e.isCancelled() || e.getBuyer() == null) return;
        ICategoryContent c = e.getCategoryContent();
        String id = c == null ? "" : c.getIdentifier();
        String item = id.substring(id.lastIndexOf('.') + 1).replace('-', '_').toLowerCase(Locale.ROOT);
        J j = new J().s("player", e.getBuyer().getName()).s("item", item).s("item_id", id);
        List<IContentTier> tiers = c == null ? null : c.getContentTiers();
        if (tiers != null && tiers.size() == 1) j.i("cost", tiers.get(0).getPrice()).s("currency", lower(tiers.get(0).getCurrency()));
        IArena a = e.getArena() != null ? e.getArena() : arenaOf(e.getBuyer());
        ev("purchase", j.s("arena", a == null ? "" : a.getArenaName()));
    }
    @EventHandler(priority = EventPriority.MONITOR) public void onUpgrade(UpgradeBuyEvent e) {
        ev("upgrade", new J().s("player", e.getPlayer().getName()).s("upgrade", e.getTeamUpgrade().getName()).s("arena", e.getArena().getArenaName()));
    }
    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true) public void onPickup(PlayerPickupItemEvent e) {
        IArena a = arenaOf(e.getPlayer()); if (a == null) return;
        ItemStack it = e.getItem().getItemStack();
        ev("pickup", new J().s("player", e.getPlayer().getName()).s("item", lower(it.getType())).i("count", Math.max(0, it.getAmount() - e.getRemaining())).s("arena", a.getArenaName()));
    }
    void blockEv(String type, Player p, org.bukkit.block.Block bl) {
        IArena a = arenaOf(p); if (a == null) return;
        ev(type, new J().s("player", p.getName()).s("block", lower(bl.getType())).i("x", bl.getX()).i("y", bl.getY()).i("z", bl.getZ()).s("arena", a.getArenaName()));
    }
    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true) public void onPlace(BlockPlaceEvent e) { blockEv("block_place", e.getPlayer(), e.getBlock()); }
    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true) public void onBreak(BlockBreakEvent e) { blockEv("block_break", e.getPlayer(), e.getBlock()); }

    // ------------------------------------------------------------ human chat never reaches the console log (kept from PlayKit)
    final Set<String> humans = Collections.newSetFromMap(new java.util.concurrent.ConcurrentHashMap<String, Boolean>());
    static final Pattern CONSOLE_CHAT = Pattern.compile("^(?:\\[[A-Z]+\\] )?(?:\\S+ )?(?:<(\\w{1,16})>|(\\w{3,16}):) ");
    static final Pattern CONSOLE_CMD = Pattern.compile("^(\\w{1,16}) issued server command: /(shout|msg|tell|w|r|me|say|bw shout)\\b", Pattern.CASE_INSENSITIVE);
    @EventHandler(priority = EventPriority.LOWEST) public void onJoinHuman(PlayerJoinEvent e) { if (!botRx.matcher(e.getPlayer().getName()).matches()) humans.add(e.getPlayer().getName()); }
    boolean hideHumanText(String txt) {
        if (txt == null) return false;
        java.util.regex.Matcher c = CONSOLE_CMD.matcher(txt);
        if (c.find()) return humans.contains(c.group(1));
        java.util.regex.Matcher m = CONSOLE_CHAT.matcher(txt.replaceAll("\u00a7.", ""));
        if (m.find()) return humans.contains(m.group(1) != null ? m.group(1) : m.group(2));
        return false;
    }
    void installConsoleFilter() {
        try {
            final Class<?> fc = Class.forName("org.apache.logging.log4j.core.Filter");
            final Class<?> rc = Class.forName("org.apache.logging.log4j.core.Filter$Result");
            final Object deny = rc.getField("DENY").get(null), neutral = rc.getField("NEUTRAL").get(null);
            Object flt = java.lang.reflect.Proxy.newProxyInstance(fc.getClassLoader(), new Class<?>[]{fc}, new java.lang.reflect.InvocationHandler() {
                public Object invoke(Object proxy, java.lang.reflect.Method m, Object[] a) throws Throwable {
                    String n = m.getName();
                    if (n.equals("filter") && a != null) {
                        for (Object o : a) {
                            String txt = null;
                            if (o instanceof CharSequence) txt = o.toString();
                            else if (o != null && o.getClass().getName().startsWith("org.apache.logging.log4j")) {
                                try { Object msg = o.getClass().getMethod("getMessage").invoke(o); txt = (String) msg.getClass().getMethod("getFormattedMessage").invoke(msg); }
                                catch (Throwable t1) { try { txt = (String) o.getClass().getMethod("getFormattedMessage").invoke(o); } catch (Throwable t2) { } }
                            }
                            if (txt != null && hideHumanText(txt)) return deny;
                        }
                        return neutral;
                    }
                    if (n.equals("getOnMatch") || n.equals("getOnMismatch")) return neutral;
                    if (m.getReturnType() == boolean.class) return true;
                    return null;
                }
            });
            Object ctx = Class.forName("org.apache.logging.log4j.LogManager").getMethod("getContext", boolean.class).invoke(null, false);
            Object cfg = ctx.getClass().getMethod("getConfiguration").invoke(ctx);
            cfg.getClass().getMethod("addFilter", fc).invoke(cfg, flt);
            ctx.getClass().getMethod("updateLoggers").invoke(ctx);
            getLogger().info("console chat filter on (human text is not logged)");
        } catch (Throwable t) { getLogger().warning("console chat filter NOT installed: " + t); }
    }

    // ------------------------------------------------------------ /tk (console, RCON or op only). Replies are one line; status is JSON.
    String statusJson() {
        StringBuilder b = new StringBuilder("{\"ms\":").append(System.currentTimeMillis()).append(",\"autojoin\":").append(js(autojoin)).append(",\"online\":");
        List<String> on = new ArrayList<>(); for (Player p : Bukkit.getOnlinePlayers()) on.add(p.getName());
        b.append(arr(on)).append(",\"arenas\":[");
        boolean first = true;
        for (IArena a : bw.getArenaUtil().getArenas()) {
            if (!first) b.append(','); first = false;
            List<String> pl = new ArrayList<>(), sp = new ArrayList<>();
            for (Player p : a.getPlayers()) pl.add(p.getName());
            for (Player p : a.getSpectators()) sp.add(p.getName());
            Match m = matches.get(a.getArenaName());
            b.append("{\"name\":").append(js(a.getArenaName())).append(",\"state\":").append(js(st(a.getStatus()))).append(",\"group\":").append(js(String.valueOf(a.getGroup())))
             .append(",\"players\":").append(arr(pl)).append(",\"spectators\":").append(arr(sp))
             .append(",\"match_id\":").append(m == null ? "null" : js(m.id)).append(",\"started_ms\":").append(m == null ? "null" : String.valueOf(m.startMs))
             .append(",\"countdown\":").append(a.getStartingTask() == null ? "null" : String.valueOf(a.getStartingTask().getCountdown())).append(",\"teams\":[");
            boolean f2 = true;
            for (ITeam t : a.getTeams()) {
                if (!f2) b.append(','); f2 = false;
                List<String> mem = new ArrayList<>(); for (Player p : t.getMembers()) mem.add(p.getName());
                b.append("{\"team\":").append(js(t.getName())).append(",\"bed\":").append(!t.isBedDestroyed()).append(",\"members\":").append(arr(mem)).append('}');
            }
            b.append("]}");
        }
        return b.append("]}").toString();
    }
    @Override public boolean onCommand(CommandSender s, Command c, String l, String[] a) {
        if (!s.isOp() && !(s instanceof ConsoleCommandSender) && !(s instanceof RemoteConsoleCommandSender)) { s.sendMessage("no"); return true; }
        String sub = a.length > 0 ? a[0].toLowerCase(Locale.ROOT) : "status";
        if (sub.equals("status")) { s.sendMessage(statusJson()); return true; }
        if (sub.equals("truth")) { ticksOn = a.length > 1 && a[1].equals("on"); s.sendMessage("{\"ok\":true,\"ticks\":" + ticksOn + "}"); return true; }
        if (sub.equals("autojoin")) {
            if (a.length < 2) { s.sendMessage("{\"ok\":true,\"autojoin\":" + js(autojoin) + "}"); return true; }
            String v = a[1].equalsIgnoreCase("off") ? "" : a[1];
            if (!v.isEmpty() && bw.getArenaUtil().getArenaByName(v) == null) { s.sendMessage("{\"ok\":false,\"error\":\"no arena " + v.replaceAll("[^A-Za-z0-9_\\-]", "") + "\"}"); return true; }
            setAutojoin(v); s.sendMessage("{\"ok\":true,\"autojoin\":" + js(v) + "}"); return true;
        }
        if (sub.equals("join") && a.length >= 3) {
            Player p = Bukkit.getPlayerExact(a[1]); IArena ar = bw.getArenaUtil().getArenaByName(a[2]);
            if (p == null || ar == null) { s.sendMessage("{\"ok\":false,\"error\":\"" + (p == null ? "player not online" : "no such arena") + "\"}"); return true; }
            IArena cur = arenaOf(p);
            if (cur == null) p.performCommand("bw join " + ar.getArenaName());
            IArena now = arenaOf(p);
            s.sendMessage("{\"ok\":" + (now != null && now.getArenaName().equals(ar.getArenaName())) + ",\"arena\":" + js(now == null ? null : now.getArenaName()) + ",\"command\":\"bw join " + ar.getArenaName() + "\"}");
            return true;
        }
        if (sub.equals("start") && a.length >= 2) {
            IArena ar = bw.getArenaUtil().getArenaByName(a[1]);
            if (ar == null) { s.sendMessage("{\"ok\":false,\"error\":\"no such arena\"}"); return true; }
            if (ar.getStatus() == GameState.playing) { s.sendMessage("{\"ok\":true,\"state\":\"playing\",\"note\":\"already playing\"}"); return true; }
            Player who = null;
            for (Player p : ar.getPlayers()) if (botRx.matcher(p.getName()).matches()) { who = p; break; }
            if (who == null) { s.sendMessage("{\"ok\":false,\"error\":\"no Glim player in the arena\"}"); return true; }
            // BedWars1058's own command, run as the player (CmdStart needs a player in the arena; "debug" + op starts it with one player)
            boolean wasOp = who.isOp();
            try { if (!wasOp) who.setOp(true); who.performCommand("bw forceStart debug"); }
            finally { if (!wasOp) who.setOp(false); }
            s.sendMessage("{\"ok\":" + (ar.getStatus() == GameState.starting || ar.getStatus() == GameState.playing) + ",\"state\":" + js(st(ar.getStatus()))
                    + ",\"countdown\":" + (ar.getStartingTask() == null ? "null" : String.valueOf(ar.getStartingTask().getCountdown())) + ",\"command\":\"bw forceStart debug\",\"as\":" + js(who.getName()) + "}");
            return true;
        }
        if (sub.equals("stop") && a.length >= 2) {
            int n = 0;
            for (IArena ar : new ArrayList<>(bw.getArenaUtil().getArenas())) {
                if (!a[1].equals("all") && !ar.getArenaName().equals(a[1])) continue;
                if (ar.getStatus() == GameState.playing) { ar.changeStatus(GameState.restarting); n++; }
                else if (ar.getStatus() == GameState.waiting || ar.getStatus() == GameState.starting) {
                    for (Player p : new ArrayList<>(ar.getPlayers())) { p.performCommand("bw leave"); n++; }
                }
            }
            s.sendMessage("{\"ok\":true,\"stopped\":" + n + "}");
            return true;
        }
        if (sub.equals("nudge") && a.length >= 5) {   // a short push for tests: velocity in blocks/tick, each part clamped to +-1
            Player p = Bukkit.getPlayerExact(a[1]);
            if (p == null) { s.sendMessage("{\"ok\":false,\"error\":\"player not online\"}"); return true; }
            try {
                double vx = Math.max(-1, Math.min(1, Double.parseDouble(a[2]))), vy = Math.max(-1, Math.min(1, Double.parseDouble(a[3]))), vz = Math.max(-1, Math.min(1, Double.parseDouble(a[4])));
                p.setVelocity(new Vector(vx, vy, vz));
                Location lo = p.getLocation();
                s.sendMessage("{\"ok\":true,\"x\":" + f(lo.getX()) + ",\"y\":" + f(lo.getY()) + ",\"z\":" + f(lo.getZ()) + "}");
            } catch (NumberFormatException ex) { s.sendMessage("{\"ok\":false,\"error\":\"bad number\"}"); }
            return true;
        }
        s.sendMessage("{\"ok\":false,\"error\":\"usage: tk status | autojoin <arena|off> | join <player> <arena> | start <arena> | stop <arena|all> | nudge <player> vx vy vz | truth on|off\"}");
        return true;
    }
}
